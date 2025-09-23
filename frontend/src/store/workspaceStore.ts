/**
 * Zustand store for workspace and permission state management
 * Phase 3B: Advanced UI & Full Workspace Experience
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type {
  WorkspaceCreate,
  WorkspaceUpdate,
  PermissionCreate,
  PermissionUpdate,
  EffectivePermissionResult,
  WorkspaceStore
} from '../types/workspace'
import { workspaceApi, WorkspaceApiError } from '../services/workspaceApi'

export const useWorkspaceStore = create<WorkspaceStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      workspaces: [],
      activeWorkspace: null,
      permissions: [],
      isLoading: false,
      error: null,

      // Workspace actions
      fetchWorkspaces: async () => {
        set({ isLoading: true, error: null })
        try {
          const data = await workspaceApi.getWorkspaces()
          const { workspaces, active_workspace_id } = data

          // Find active workspace by ID from API response (more reliable than is_active flag)
          const activeWorkspace = active_workspace_id
            ? workspaces.find(w => w.id === active_workspace_id) || null
            : workspaces.find(w => w.is_active) || null // Fallback to is_active flag

          set({ workspaces, activeWorkspace, isLoading: false })
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to fetch workspaces'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      createWorkspace: async (data: WorkspaceCreate) => {
        set({ isLoading: true, error: null })
        try {
          const newWorkspace = await workspaceApi.createWorkspace(data)
          const workspaces = [...get().workspaces, newWorkspace]

          // If this is set as active, update active workspace
          const activeWorkspace = newWorkspace.is_active ? newWorkspace : get().activeWorkspace

          set({ workspaces, activeWorkspace, isLoading: false })
          return newWorkspace
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to create workspace'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      updateWorkspace: async (id: number, data: WorkspaceUpdate) => {
        set({ isLoading: true, error: null })
        try {
          const updatedWorkspace = await workspaceApi.updateWorkspace(id, data)
          const workspaces = get().workspaces.map(w =>
            w.id === id ? updatedWorkspace : w
          )

          // Update active workspace if necessary
          const activeWorkspace = updatedWorkspace.is_active
            ? updatedWorkspace
            : get().activeWorkspace?.id === id
              ? null
              : get().activeWorkspace

          set({ workspaces, activeWorkspace, isLoading: false })
          return updatedWorkspace
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to update workspace'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      deleteWorkspace: async (id: number) => {
        set({ isLoading: true, error: null })
        try {
          await workspaceApi.deleteWorkspace(id)
          const workspaces = get().workspaces.filter(w => w.id !== id)
          const activeWorkspace = get().activeWorkspace?.id === id
            ? null
            : get().activeWorkspace

          set({ workspaces, activeWorkspace, isLoading: false })
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to delete workspace'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      activateWorkspace: async (id: number) => {
        set({ isLoading: true, error: null })
        try {
          const activatedWorkspace = await workspaceApi.activateWorkspace(id)

          // Deactivate all other workspaces and activate the selected one
          const workspaces = get().workspaces.map(w => ({
            ...w,
            is_active: w.id === id
          }))

          set({
            workspaces,
            activeWorkspace: activatedWorkspace,
            isLoading: false,
            // Clear permissions when switching workspaces
            permissions: []
          })

          // Fetch permissions for the newly active workspace
          get().fetchPermissions(id)
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to activate workspace'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      // Permission actions
      fetchPermissions: async (workspaceId: number) => {
        // Safety check: don't fetch permissions if no valid workspace ID
        if (!workspaceId || workspaceId <= 0) {
          console.warn('fetchPermissions called with invalid workspace ID:', workspaceId)
          set({ permissions: [], isLoading: false })
          return
        }

        set({ isLoading: true, error: null })
        try {
          const permissions = await workspaceApi.getWorkspacePermissions(workspaceId)
          set({ permissions, isLoading: false })
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to fetch permissions'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      addPermission: async (workspaceId: number, data: PermissionCreate) => {
        set({ isLoading: true, error: null })
        try {
          const newPermission = await workspaceApi.createPermission(workspaceId, data)
          const permissions = [...get().permissions, newPermission]
          set({ permissions, isLoading: false })
          return newPermission
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to add permission'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      updatePermission: async (id: number, data: PermissionUpdate) => {
        set({ isLoading: true, error: null })
        try {
          const updatedPermission = await workspaceApi.updatePermission(id, data)
          const permissions = get().permissions.map(p =>
            p.id === id ? updatedPermission : p
          )
          set({ permissions, isLoading: false })
          return updatedPermission
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to update permission'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      deletePermission: async (id: number) => {
        set({ isLoading: true, error: null })
        try {
          await workspaceApi.deletePermission(id)
          const permissions = get().permissions.filter(p => p.id !== id)
          set({ permissions, isLoading: false })
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to delete permission'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      // Batch operations
      getBatchEffectivePermissions: async (workspaceId: number, paths: string[]): Promise<EffectivePermissionResult[]> => {
        // Safety check: don't fetch permissions if no valid workspace ID
        if (!workspaceId || workspaceId <= 0) {
          console.warn('getBatchEffectivePermissions called with invalid workspace ID:', workspaceId)
          return []
        }

        try {
          const response = await workspaceApi.getBatchEffectivePermissions(workspaceId, paths)
          return response.results
        } catch (error) {
          const errorMessage = error instanceof WorkspaceApiError
            ? error.message
            : 'Failed to get effective permissions'
          set({ error: errorMessage })
          throw error
        }
      },

      // Utility actions
      clearError: () => set({ error: null }),
      setLoading: (loading: boolean) => set({ isLoading: loading }),
    }),
    {
      name: 'workspace-store', // Name for devtools
    }
  )
)

// Utility hook to get active workspace ID
export const useActiveWorkspaceId = (): number | null => {
  return useWorkspaceStore(state => state.activeWorkspace?.id || null)
}

// Utility hook to check if a workspace is active
export const useIsWorkspaceActive = (workspaceId: number): boolean => {
  return useWorkspaceStore(state => state.activeWorkspace?.id === workspaceId)
}