// Web UI specific types
export interface FileItem {
  id: string;
  name: string;
  path: string;
  size: number;
  type: 'file' | 'folder';
  permission: 'read-only' | 'read-write' | 'agent-controlled';
  category?: string;
  modified: Date;
  selected?: boolean;
  expanded?: boolean;
  children?: FileItem[];
}

export interface FolderTreeNode {
  id: string;
  name: string;
  path: string;
  type: 'folder' | 'file';
  permission: 'read-only' | 'read-write' | 'agent-controlled';
  children?: FolderTreeNode[];
  expanded?: boolean;
}

export interface UIState {
  currentView: 'explorer' | 'list';
  selectedFiles: string[];
  selectedFolder?: string;
  searchQuery: string;
  filters: {
    permissions: ('read-only' | 'read-write' | 'agent-controlled')[];
    fileTypes: string[];
    categories: string[];
    sizeRange?: {
      min: number;
      max: number;
    };
    dateRange?: {
      start: Date;
      end: Date;
    };
  };
  sorting: {
    field: 'name' | 'type' | 'size' | 'modified' | 'permission' | 'category';
    direction: 'asc' | 'desc';
  };
}

export interface DraggedFile {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'folder';
  permission: 'read-only' | 'read-write' | 'agent-controlled';
}

export interface DropResult {
  targetPath: string;
  targetPermission: 'read-only' | 'read-write' | 'agent-controlled';
}

export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface FileOperationResult {
  success: boolean;
  files?: FileItem[];
  message?: string;
  error?: string;
}

export interface PermissionUpdateResult {
  success: boolean;
  updatedFiles: string[];
  message?: string;
  error?: string;
}

export interface SystemStatus {
  healthy: boolean;
  components: {
    fileSystem: boolean;
    permissions: boolean;
    webSocket: boolean;
  };
  stats: {
    totalFiles: number;
    readOnlyFiles: number;
    readWriteFiles: number;
    agentFiles: number;
    totalSize: number;
  };
}

export interface WebSocketMessage {
  type: 'file-added' | 'file-changed' | 'file-removed' | 'permission-changed' | 'system-status';
  data: any;
  timestamp: Date;
}

export interface SearchFilters {
  query?: string;
  permissions?: ('read-only' | 'read-write' | 'agent-controlled')[];
  fileTypes?: string[];
  categories?: string[];
  sizeMin?: number;
  sizeMax?: number;
  dateFrom?: Date;
  dateTo?: Date;
}

export interface SortOptions {
  field: 'name' | 'type' | 'size' | 'modified' | 'permission' | 'category';
  direction: 'asc' | 'desc';
}

export interface ToastNotification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  actions?: {
    label: string;
    action: () => void;
  }[];
}

export interface ContextMenuOption {
  id: string;
  label: string;
  icon?: string;
  action: () => void;
  disabled?: boolean;
  separator?: boolean;
}

export interface BreadcrumbItem {
  label: string;
  path: string;
  permission?: 'read-only' | 'read-write' | 'agent-controlled';
}

// Re-export types from the main project that we need in the UI
// Removed circular import - these types should be defined directly in this file