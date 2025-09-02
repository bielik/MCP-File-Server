import { APIResponse, FileItem, FileOperationResult, PermissionUpdateResult, SystemStatus, SearchFilters, SortOptions } from '../types/index.js';

const API_BASE = __API_BASE_URL__ || '';

class APIService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    try {
      const url = `${this.baseUrl}/api${endpoint}`;
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      console.error(`API Error (${endpoint}):`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
      };
    }
  }

  // File Operations
  async getFiles(filters?: SearchFilters, sort?: SortOptions): Promise<APIResponse<FileItem[]>> {
    const params = new URLSearchParams();
    
    if (filters) {
      if (filters.query) params.append('query', filters.query);
      if (filters.permissions) params.append('permissions', filters.permissions.join(','));
      if (filters.fileTypes) params.append('fileTypes', filters.fileTypes.join(','));
      if (filters.categories) params.append('categories', filters.categories.join(','));
      if (filters.sizeMin) params.append('sizeMin', filters.sizeMin.toString());
      if (filters.sizeMax) params.append('sizeMax', filters.sizeMax.toString());
      if (filters.dateFrom) params.append('dateFrom', filters.dateFrom.toISOString());
      if (filters.dateTo) params.append('dateTo', filters.dateTo.toISOString());
    }
    
    if (sort) {
      params.append('sortField', sort.field);
      params.append('sortDirection', sort.direction);
    }

    const queryString = params.toString();
    const endpoint = queryString ? `/files?${queryString}` : '/files';
    
    return this.request<FileItem[]>(endpoint);
  }

  async getFolderStructure(basePath?: string): Promise<APIResponse<FileItem>> {
    const params = basePath ? `?basePath=${encodeURIComponent(basePath)}` : '';
    return this.request<FileItem>(`/files/structure${params}`);
  }

  async getFileContent(filePath: string): Promise<APIResponse<{ content: string; metadata: any }>> {
    return this.request<{ content: string; metadata: any }>(`/files/content`, {
      method: 'POST',
      body: JSON.stringify({ filePath }),
    });
  }

  async saveFileContent(filePath: string, content: string): Promise<APIResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/files/content`, {
      method: 'PUT',
      body: JSON.stringify({ filePath, content }),
    });
  }

  async createFile(filePath: string, content: string = '', createDirectories: boolean = true): Promise<APIResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/files`, {
      method: 'POST',
      body: JSON.stringify({ filePath, content, createDirectories }),
    });
  }

  async deleteFile(filePath: string): Promise<APIResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/files`, {
      method: 'DELETE',
      body: JSON.stringify({ filePath }),
    });
  }

  async moveFile(sourcePath: string, targetPath: string): Promise<APIResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/files/move`, {
      method: 'POST',
      body: JSON.stringify({ sourcePath, targetPath }),
    });
  }

  // Permission Management
  async updateFilePermissions(
    filePaths: string[],
    permission: 'read-only' | 'read-write' | 'agent-controlled'
  ): Promise<APIResponse<PermissionUpdateResult>> {
    return this.request<PermissionUpdateResult>(`/permissions`, {
      method: 'PUT',
      body: JSON.stringify({ filePaths, permission }),
    });
  }

  async getPermissionMatrix(): Promise<APIResponse<{
    contextFolders: string[];
    workingFolders: string[];
    outputFolder: string;
  }>> {
    return this.request(`/permissions/matrix`);
  }

  async updatePermissionMatrix(matrix: {
    contextFolders?: string[];
    workingFolders?: string[];
    outputFolder?: string;
  }): Promise<APIResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/permissions/matrix`, {
      method: 'PUT',
      body: JSON.stringify(matrix),
    });
  }

  // Search Operations
  async searchFiles(
    query: string,
    searchType: 'text' | 'semantic' | 'multimodal' = 'text',
    options?: {
      categories?: string[];
      fileTypes?: string[];
      maxResults?: number;
    }
  ): Promise<APIResponse<{
    results: Array<{
      id: string;
      path: string;
      snippet: string;
      relevance: number;
      type: 'text' | 'image';
    }>;
    query: string;
    searchType: string;
    totalResults: number;
    searchTime: number;
  }>> {
    return this.request(`/search`, {
      method: 'POST',
      body: JSON.stringify({
        query,
        searchType,
        ...options,
      }),
    });
  }

  // System Status and Health
  async getSystemStatus(): Promise<APIResponse<SystemStatus>> {
    return this.request<SystemStatus>(`/system/status`);
  }

  async getSystemHealth(): Promise<APIResponse<{
    healthy: boolean;
    components: Array<{
      name: string;
      healthy: boolean;
      message: string;
    }>;
  }>> {
    return this.request(`/system/health`);
  }

  // File Upload
  async uploadFile(file: File, targetPath: string, overwrite: boolean = false): Promise<APIResponse<{ success: boolean; path: string }>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('targetPath', targetPath);
    formData.append('overwrite', overwrite.toString());

    try {
      const response = await fetch(`${this.baseUrl}/api/files/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Upload failed',
      };
    }
  }

  // Batch Operations
  async batchOperation(operation: 'delete' | 'move' | 'permission', files: string[], options?: any): Promise<APIResponse<{
    success: boolean;
    results: Array<{
      file: string;
      success: boolean;
      error?: string;
    }>;
  }>> {
    return this.request(`/files/batch`, {
      method: 'POST',
      body: JSON.stringify({
        operation,
        files,
        options,
      }),
    });
  }

  // Statistics and Analytics
  async getFileStatistics(): Promise<APIResponse<{
    totalFiles: number;
    totalSize: number;
    filesByType: Record<string, number>;
    filesByPermission: Record<string, number>;
    recentlyModified: FileItem[];
    largestFiles: FileItem[];
  }>> {
    return this.request(`/files/statistics`);
  }
}

// Export singleton instance
export const apiService = new APIService();
export default apiService;