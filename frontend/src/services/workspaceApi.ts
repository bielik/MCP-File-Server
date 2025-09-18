/**
 * API service for workspace and permission operations
 * Phase 3B: Advanced UI & Full Workspace Experience
 */

import type {
  Workspace,
  WorkspaceCreate,
  WorkspaceUpdate,
  Permission,
  PermissionCreate,
  PermissionUpdate,
  BatchEffectivePermissionsRequest,
  BatchEffectivePermissionsResponse,
  ApiError
} from '../types/workspace'

const API_BASE_URL = 'http://localhost:8000/api'

class WorkspaceApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number,
    public details?: any
  ) {
    super(message)
    this.name = 'WorkspaceApiError'
  }
}

async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ApiError
    try {
      errorData = await response.json()
    } catch {
      errorData = {
        code: 'UNKNOWN_ERROR',
        message: `HTTP ${response.status}: ${response.statusText}`
      }
    }

    throw new WorkspaceApiError(
      errorData.message,
      errorData.code,
      response.status,
      errorData.details
    )
  }

  return response.json()
}

// Workspace API operations
export const workspaceApi = {
  // Get all workspaces
  async getWorkspaces(): Promise<Workspace[]> {
    const response = await fetch(`${API_BASE_URL}/workspaces`)
    const data = await handleApiResponse<{ workspaces: Workspace[] }>(response)
    return data.workspaces
  },

  // Get specific workspace
  async getWorkspace(id: number): Promise<Workspace> {
    const response = await fetch(`${API_BASE_URL}/workspaces/${id}`)
    return handleApiResponse<Workspace>(response)
  },

  // Create new workspace
  async createWorkspace(data: WorkspaceCreate): Promise<Workspace> {
    const response = await fetch(`${API_BASE_URL}/workspaces`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    return handleApiResponse<Workspace>(response)
  },

  // Update workspace
  async updateWorkspace(id: number, data: WorkspaceUpdate): Promise<Workspace> {
    const response = await fetch(`${API_BASE_URL}/workspaces/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    return handleApiResponse<Workspace>(response)
  },

  // Delete workspace
  async deleteWorkspace(id: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/workspaces/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      await handleApiResponse(response) // This will throw the error
    }
  },

  // Activate workspace
  async activateWorkspace(id: number): Promise<Workspace> {
    const response = await fetch(`${API_BASE_URL}/workspaces/${id}/activate`, {
      method: 'POST',
    })
    return handleApiResponse<Workspace>(response)
  },

  // Get workspace permissions
  async getWorkspacePermissions(workspaceId: number): Promise<Permission[]> {
    const response = await fetch(`${API_BASE_URL}/workspaces/${workspaceId}/permissions`)
    const data = await handleApiResponse<{ permissions: Permission[] }>(response)
    return data.permissions
  },

  // Create permission
  async createPermission(workspaceId: number, data: PermissionCreate): Promise<Permission> {
    const response = await fetch(`${API_BASE_URL}/workspaces/${workspaceId}/permissions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    return handleApiResponse<Permission>(response)
  },

  // Update permission
  async updatePermission(permissionId: number, data: PermissionUpdate): Promise<Permission> {
    const response = await fetch(`${API_BASE_URL}/permissions/${permissionId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    return handleApiResponse<Permission>(response)
  },

  // Delete permission
  async deletePermission(permissionId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/permissions/${permissionId}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      await handleApiResponse(response)
    }
  },

  // Get batch effective permissions (cornerstone API for UI)
  async getBatchEffectivePermissions(
    workspaceId: number,
    paths: string[]
  ): Promise<BatchEffectivePermissionsResponse> {
    const response = await fetch(
      `${API_BASE_URL}/workspaces/${workspaceId}/effective-permissions:batch`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ paths } as BatchEffectivePermissionsRequest),
      }
    )
    return handleApiResponse<BatchEffectivePermissionsResponse>(response)
  },

  // Get active workspace permissions (legacy endpoint support)
  async getActiveWorkspacePermissions(): Promise<Permission[]> {
    const response = await fetch(`${API_BASE_URL}/active-workspace/permissions`)
    const data = await handleApiResponse<{ permissions: Permission[] }>(response)
    return data.permissions
  },
}

// File browser API operations (reuse existing endpoint)
export const fileApi = {
  // Browse files with pagination
  async browseFiles(
    path: string = '',
    page: number = 1,
    pageSize: number = 100,
    maxDepth: number = 1
  ) {
    const params = new URLSearchParams({
      path,
      page: page.toString(),
      pageSize: pageSize.toString(),
      maxDepth: maxDepth.toString(),
    })

    const response = await fetch(`${API_BASE_URL}/browse?${params}`)
    return handleApiResponse<{
      files: Array<{
        name: string
        path: string
        is_directory: boolean
        size?: number
        modified?: string
      }>
      total_count: number
      page: number
      page_size: number
      total_pages: number
    }>(response)
  },
}

// Export error class for error handling
export { WorkspaceApiError }