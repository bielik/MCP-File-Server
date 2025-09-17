/**
 * TypeScript interfaces for Workspace and Permission management
 * Phase 3B: Advanced UI & Full Workspace Experience
 */

// Base workspace interface matching backend model
export interface Workspace {
  id: number
  name: string
  description: string | null
  is_active: boolean
  version: number
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

// Interface for creating new workspaces
export interface WorkspaceCreate {
  name: string
  description?: string
  is_active?: boolean
}

// Interface for updating workspaces
export interface WorkspaceUpdate {
  name?: string
  description?: string
  is_active?: boolean
}

// Permission interface matching backend model
export interface Permission {
  id: number
  workspace_id: number
  path: string
  permission_type: 'read' | 'write'
  rule_type: 'allow' | 'deny'
  description: string | null
  version: number
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

// Interface for creating new permissions
export interface PermissionCreate {
  path: string
  permission_type: 'read' | 'write'
  rule_type: 'allow' | 'deny'
  description?: string
}

// Interface for updating permissions
export interface PermissionUpdate {
  path?: string
  permission_type?: 'read' | 'write'
  rule_type?: 'allow' | 'deny'
  description?: string
}

// Effective permission result from batch API
export interface EffectivePermissionResult {
  path: string
  status: 'none' | 'read' | 'write'
  matchedRule: MatchedRule | null
}

// Matched rule information for permission inspector
export interface MatchedRule {
  id: string
  path: string
  permission_type: 'read' | 'write'
  rule_type: 'allow' | 'deny'
  description: string
  workspace_id: number
  precedence_reason: string
}

// Batch API request/response interfaces
export interface BatchEffectivePermissionsRequest {
  paths: string[]
}

export interface BatchEffectivePermissionsResponse {
  results: EffectivePermissionResult[]
}

// WebSocket message types for real-time updates
export interface WebSocketMessage {
  type: 'workspace_activated' | 'workspace_deactivated' | 'permissions_updated' | 'cache_cleared'
  data: any
}

export interface WorkspaceActivatedMessage extends WebSocketMessage {
  type: 'workspace_activated'
  data: {
    workspaceId: number
    workspaceName: string
  }
}

export interface PermissionsUpdatedMessage extends WebSocketMessage {
  type: 'permissions_updated'
  data: {
    workspaceId: number
    permissionId: number
    action: 'created' | 'updated' | 'deleted'
  }
}

// UI-specific interfaces
export interface FileTreeNode {
  path: string
  name: string
  isDirectory: boolean
  children?: FileTreeNode[]
  expanded?: boolean
  selected?: boolean
  permission?: EffectivePermissionResult
}

// Component prop interfaces
export interface WorkspaceManagerProps {
  className?: string
}

export interface TwoPanelPermissionEditorProps {
  workspaceId: number
  className?: string
}

export interface PermissionInspectorProps {
  path: string
  permissionResult: EffectivePermissionResult
  onClose?: () => void
}

// API response interfaces
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface ApiError {
  code: string
  message: string
  details?: any
}

// Store interfaces
export interface WorkspaceStore {
  // State
  workspaces: Workspace[]
  activeWorkspace: Workspace | null
  permissions: Permission[]
  isLoading: boolean
  error: string | null

  // Actions
  fetchWorkspaces: () => Promise<void>
  createWorkspace: (data: WorkspaceCreate) => Promise<Workspace>
  updateWorkspace: (id: number, data: WorkspaceUpdate) => Promise<Workspace>
  deleteWorkspace: (id: number) => Promise<void>
  activateWorkspace: (id: number) => Promise<void>

  // Permission actions
  fetchPermissions: (workspaceId: number) => Promise<void>
  addPermission: (workspaceId: number, data: PermissionCreate) => Promise<Permission>
  updatePermission: (id: number, data: PermissionUpdate) => Promise<Permission>
  deletePermission: (id: number) => Promise<void>

  // Batch operations
  getBatchEffectivePermissions: (workspaceId: number, paths: string[]) => Promise<EffectivePermissionResult[]>

  // Utility actions
  clearError: () => void
  setLoading: (loading: boolean) => void
}