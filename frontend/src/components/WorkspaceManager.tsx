/**
 * Workspace Manager Component
 * Phase 3B: Advanced UI & Full Workspace Experience
 *
 * Handles workspace CRUD operations with create/delete/activate functionality
 */

import React, { useState, useEffect } from 'react'
import { useWorkspaceStore } from '../store/workspaceStore'
import { useWebSocketContext } from '../contexts/WebSocketContext'
import type { WorkspaceCreate, WorkspaceManagerProps } from '../types/workspace'

interface CreateWorkspaceModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: WorkspaceCreate) => Promise<void>
}

function CreateWorkspaceModal({ isOpen, onClose, onSubmit }: CreateWorkspaceModalProps) {
  const [formData, setFormData] = useState<WorkspaceCreate>({
    name: '',
    description: '',
    is_active: false,
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      setFormError('Workspace name is required')
      return
    }

    setIsSubmitting(true)
    setFormError(null)

    try {
      await onSubmit(formData)
      setFormData({ name: '', description: '', is_active: false })
      onClose()
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Failed to create workspace')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      setFormData({ name: '', description: '', is_active: false })
      setFormError(null)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Create New Workspace</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Workspace Name *
            </label>
            <input
              type="text"
              id="name"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="e.g., Development, Research, Personal"
              disabled={isSubmitting}
              required
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="Describe the purpose of this workspace..."
              rows={3}
              disabled={isSubmitting}
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
              className="h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300 rounded"
              disabled={isSubmitting}
            />
            <label htmlFor="is_active" className="ml-2 block text-sm text-gray-700">
              Set as active workspace
            </label>
          </div>

          {formError && (
            <div className="text-red-600 text-sm bg-red-50 p-2 rounded">
              {formError}
            </div>
          )}

          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Creating...' : 'Create Workspace'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

interface DeleteConfirmModalProps {
  isOpen: boolean
  workspaceName: string
  onClose: () => void
  onConfirm: () => Promise<void>
}

function DeleteConfirmModal({ isOpen, workspaceName, onClose, onConfirm }: DeleteConfirmModalProps) {
  const [isDeleting, setIsDeleting] = useState(false)

  const handleConfirm = async () => {
    setIsDeleting(true)
    try {
      await onConfirm()
      onClose()
    } catch (error) {
      console.error('Failed to delete workspace:', error)
      // Error handling is done in the parent component
    } finally {
      setIsDeleting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Delete Workspace</h2>

        <p className="text-gray-600 mb-6">
          Are you sure you want to delete the workspace <strong>"{workspaceName}"</strong>?
          This action cannot be undone and will permanently remove all permissions associated with this workspace.
        </p>

        <div className="flex space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors"
            disabled={isDeleting}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isDeleting}
          >
            {isDeleting ? 'Deleting...' : 'Delete Workspace'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function WorkspaceManager({ className = '' }: WorkspaceManagerProps) {
  const {
    workspaces,
    isLoading,
    error,
    fetchWorkspaces,
    createWorkspace,
    deleteWorkspace,
    activateWorkspace,
    clearError,
  } = useWorkspaceStore()

  const { isConnected } = useWebSocketContext()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [deleteWorkspaceId, setDeleteWorkspaceId] = useState<number | null>(null)

  // Fetch workspaces on component mount
  useEffect(() => {
    fetchWorkspaces()
  }, [fetchWorkspaces])

  const handleCreateWorkspace = async (data: WorkspaceCreate) => {
    await createWorkspace(data)
  }

  const handleActivateWorkspace = async (workspaceId: number) => {
    try {
      await activateWorkspace(workspaceId)
    } catch (error) {
      console.error('Failed to activate workspace:', error)
    }
  }

  const handleDeleteWorkspace = async () => {
    if (deleteWorkspaceId) {
      await deleteWorkspace(deleteWorkspaceId)
      setDeleteWorkspaceId(null)
    }
  }

  const workspaceToDelete = workspaces.find(w => w.id === deleteWorkspaceId)

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Workspace Management</h2>
          <p className="text-gray-400 mt-1">
            Create and manage isolated permission contexts for different tasks
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors font-medium"
          disabled={isLoading}
        >
          + Create Workspace
        </button>
      </div>

      {/* Connection Status */}
      <div className="flex items-center space-x-4 text-sm">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className="text-gray-400">
            WebSocket: {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${!isLoading ? 'bg-green-400' : 'bg-yellow-400'}`} />
          <span className="text-gray-400">
            {isLoading ? 'Loading...' : `${workspaces.length} workspaces`}
          </span>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded-lg flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={clearError}
            className="text-red-400 hover:text-red-300 ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* Workspace List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workspaces.map((workspace) => (
          <div
            key={workspace.id}
            className={`bg-gray-800 rounded-lg p-4 border-2 transition-all ${
              workspace.is_active
                ? 'border-cyan-500 bg-cyan-900 bg-opacity-30'
                : 'border-gray-700 hover:border-gray-600'
            }`}
          >
            {/* Workspace Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-white truncate">
                  {workspace.name}
                </h3>
                {workspace.is_active && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 mt-1">
                    ● Active
                  </span>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex space-x-1 ml-2">
                {!workspace.is_active && (
                  <button
                    onClick={() => handleActivateWorkspace(workspace.id)}
                    className="p-1 text-gray-400 hover:text-cyan-400 transition-colors"
                    title="Activate workspace"
                    disabled={isLoading}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </button>
                )}
                <button
                  onClick={() => setDeleteWorkspaceId(workspace.id)}
                  className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                  title="Delete workspace"
                  disabled={isLoading || workspace.is_active}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Workspace Description */}
            {workspace.description && (
              <p className="text-gray-300 text-sm mb-3 line-clamp-2">
                {workspace.description}
              </p>
            )}

            {/* Workspace Metadata */}
            <div className="text-xs text-gray-500 space-y-1">
              <div>
                Created: {new Date(workspace.created_at).toLocaleDateString()}
              </div>
              <div>
                ID: {workspace.id}
              </div>
            </div>
          </div>
        ))}

        {/* Empty State */}
        {workspaces.length === 0 && !isLoading && (
          <div className="col-span-full text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-300 mb-2">No workspaces yet</h3>
            <p className="text-gray-400 mb-4">
              Create your first workspace to start organizing your file permissions
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
            >
              Create First Workspace
            </button>
          </div>
        )}
      </div>

      {/* Create Workspace Modal */}
      <CreateWorkspaceModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateWorkspace}
      />

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={deleteWorkspaceId !== null}
        workspaceName={workspaceToDelete?.name || ''}
        onClose={() => setDeleteWorkspaceId(null)}
        onConfirm={handleDeleteWorkspace}
      />
    </div>
  )
}