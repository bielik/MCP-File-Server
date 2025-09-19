/**
 * Two-Panel Permission Editor Component
 * Phase 3B: Advanced UI & Full Workspace Experience
 *
 * Left panel: File tree browser with selection
 * Right panel: Permission rules management with batch API integration
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useWorkspaceStore } from '../store/workspaceStore'
import { fileApi } from '../services/workspaceApi'
import PermissionInspector from './PermissionInspector'
import type {
  TwoPanelPermissionEditorProps,
  FileTreeNode,
  EffectivePermissionResult,
  PermissionCreate
} from '../types/workspace'

interface FileTreeProps {
  nodes: FileTreeNode[]
  onNodeSelect: (path: string, selected: boolean) => void
  onNodeExpand: (path: string) => void
  selectedPaths: Set<string>
  expandedPaths: Set<string>
  permissionResults: Map<string, EffectivePermissionResult>
  loadingPaths: Set<string>
}

function FileTree({ nodes, onNodeSelect, onNodeExpand, selectedPaths, expandedPaths, permissionResults, loadingPaths }: FileTreeProps) {
  const renderNode = (node: FileTreeNode, depth = 0) => {
    const isSelected = selectedPaths.has(node.path)
    const isExpanded = expandedPaths.has(node.path)
    const hasChildren = node.children && node.children.length > 0
    const permissionResult = permissionResults.get(node.path)

    return (
      <div key={node.path}>
        <div
          className={`flex items-center space-x-2 py-1 px-2 ${
            isSelected ? 'bg-blue-50 border-l-2 border-blue-500' : ''
          }`}
          style={{ paddingLeft: `${depth * 20 + 8}px` }}
        >
          {/* Expand/Collapse Button */}
          {node.isDirectory && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onNodeExpand(node.path)
              }}
              className="w-4 h-4 flex items-center justify-center text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded"
              aria-label={isExpanded ? `Collapse ${node.name}` : `Expand ${node.name}`}
            >
              {isExpanded ? (
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              ) : (
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
            </button>
          )}

          {/* Checkbox for selection */}
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => onNodeSelect(node.path, e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            onClick={(e) => e.stopPropagation()}
          />

          {/* Effective Permission Dot Indicator */}
          <div className="w-4 h-4 flex items-center justify-center">
            {permissionResult && permissionResult.status === 'denied' ? (
              <span className="text-gray-400 text-sm" title="Access denied">○</span>
            ) : permissionResult && permissionResult.status === 'write' ? (
              <span className="text-green-500 text-sm" title="Write access">●</span>
            ) : permissionResult && permissionResult.status === 'read' ? (
              <span className="text-blue-500 text-sm" title="Read access">●</span>
            ) : (
              <span className="text-gray-400 text-sm" title="No access">○</span>
            )}
          </div>

          {/* File/Folder Icon and Name - clickable for folders */}
          <div
            className={`flex items-center space-x-2 flex-1 ${
              node.isDirectory ? 'cursor-pointer hover:bg-gray-50 rounded px-1' : ''
            }`}
            onClick={() => node.isDirectory ? onNodeExpand(node.path) : undefined}
          >
            {/* Icon */}
            <div className="text-gray-500">
              {node.isDirectory ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              )}
            </div>

            {/* Name */}
            <span className="flex-1 text-sm text-gray-900 truncate">{node.name}</span>
          </div>

          {/* Loading Indicator */}
          {loadingPaths.has(node.path) && (
            <div className="flex items-center space-x-1">
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-500"></div>
              <span className="text-gray-400 text-xs">Loading...</span>
            </div>
          )}

          {/* Rule Indicator - Only show for items with explicit rules on this exact path */}
          {permissionResult && permissionResult.matchedRule &&
           permissionResult.matchedRule.path === node.path && (
            <PermissionInspector
              path={node.path}
              permissionResult={permissionResult}
            />
          )}
        </div>

        {/* Render Children */}
        {node.isDirectory && isExpanded && hasChildren && (
          <div>
            {node.children!.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {nodes.map(node => renderNode(node))}
    </div>
  )
}

interface AddPermissionModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (permission: PermissionCreate) => Promise<void>
  selectedPaths: string[]
}

function AddPermissionModal({ isOpen, onClose, onSubmit, selectedPaths }: AddPermissionModalProps) {
  const [formData, setFormData] = useState<PermissionCreate>({
    path: '',
    permission_type: 'read',
    rule_type: 'allow',
    description: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && selectedPaths.length === 1) {
      setFormData(prev => ({ ...prev, path: selectedPaths[0] }))
    }
  }, [isOpen, selectedPaths])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.path.trim()) {
      setError('Path is required')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      await onSubmit(formData)
      setFormData({
        path: '',
        permission_type: 'read',
        rule_type: 'allow',
        description: '',
      })
      onClose()
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to add permission')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      setFormData({
        path: '',
        permission_type: 'read',
        rule_type: 'allow',
        description: '',
      })
      setError(null)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Add Permission Rule</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="path" className="block text-sm font-medium text-gray-700 mb-1">
              Path Pattern *
            </label>
            <input
              type="text"
              id="path"
              value={formData.path}
              onChange={(e) => setFormData(prev => ({ ...prev, path: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., projects/webapp or materials"
              disabled={isSubmitting}
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Use specific paths or parent directories to create rules
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="rule_type" className="block text-sm font-medium text-gray-700 mb-1">
                Rule Type *
              </label>
              <select
                id="rule_type"
                value={formData.rule_type}
                onChange={(e) => setFormData(prev => ({ ...prev, rule_type: e.target.value as 'allow' | 'deny' }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isSubmitting}
              >
                <option value="allow">Allow</option>
                <option value="deny">Deny</option>
              </select>
            </div>

            <div>
              <label htmlFor="permission_type" className="block text-sm font-medium text-gray-700 mb-1">
                Permission Type *
              </label>
              <select
                id="permission_type"
                value={formData.permission_type}
                onChange={(e) => setFormData(prev => ({ ...prev, permission_type: e.target.value as 'read' | 'write' }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isSubmitting}
              >
                <option value="read">Read</option>
                <option value="write">Write</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Optional description for this rule..."
              rows={2}
              disabled={isSubmitting}
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm bg-red-50 p-2 rounded">
              {error}
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
              className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Adding...' : 'Add Rule'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function TwoPanelPermissionEditor({ workspaceId, className = '' }: TwoPanelPermissionEditorProps) {
  const {
    permissions,
    fetchPermissions,
    addPermission,
    deletePermission,
    getBatchEffectivePermissions,
    isLoading,
    error,
  } = useWorkspaceStore()

  const [fileTree, setFileTree] = useState<FileTreeNode[]>([])
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set())
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set(['']))
  const [permissionResults, setPermissionResults] = useState<Map<string, EffectivePermissionResult>>(new Map())
  const [showAddModal, setShowAddModal] = useState(false)
  const [loadingPermissions, setLoadingPermissions] = useState(false)
  // Node caching for dynamic loading
  const [nodeCache, setNodeCache] = useState<Map<string, FileTreeNode[]>>(new Map())
  const [loadingPaths, setLoadingPaths] = useState<Set<string>>(new Set())

  // Fetch initial data
  useEffect(() => {
    fetchPermissions(workspaceId)
    loadFileTree()
  }, [workspaceId, fetchPermissions])

  // Load folder contents dynamically
  const loadFolderContents = async (folderPath: string): Promise<FileTreeNode[]> => {
    // Check cache first
    if (nodeCache.has(folderPath)) {
      return nodeCache.get(folderPath)!
    }

    // Mark as loading
    setLoadingPaths(prev => new Set(prev).add(folderPath))

    try {
      const response = await fileApi.browseFiles(folderPath, 1, 1000, 1)
      const children = response.files.map(file => ({
        path: file.path,
        name: file.name,
        isDirectory: file.is_directory,
        children: file.is_directory ? [] : undefined,
        expanded: expandedPaths.has(file.path),
        selected: selectedPaths.has(file.path)
      }))

      // Update cache
      setNodeCache(prev => new Map(prev).set(folderPath, children))

      // Update tree structure
      updateTreeWithChildren(folderPath, children)

      // Get permissions for newly loaded children immediately
      if (children.length > 0) {
        const childPaths = children.map(child => child.path)
        try {
          const results = await getBatchEffectivePermissions(workspaceId, childPaths)
          setPermissionResults(prev => {
            const newResults = new Map(prev)
            results.forEach(result => {
              newResults.set(result.path, result)
            })
            return newResults
          })
        } catch (error) {
          console.error('Failed to get permissions for newly loaded children:', error)
        }
      }

      return children
    } finally {
      setLoadingPaths(prev => {
        const next = new Set(prev)
        next.delete(folderPath)
        return next
      })
    }
  }

  // Load file tree from API (initial load only)
  const loadFileTree = async () => {
    try {
      const response = await fileApi.browseFiles('', 1, 1000, 1)
      const tree = buildFileTree(response.files)
      setFileTree(tree)

      // Cache root level
      const rootChildren = response.files.map(file => ({
        path: file.path,
        name: file.name,
        isDirectory: file.is_directory,
        children: file.is_directory ? [] : undefined,
        expanded: expandedPaths.has(file.path),
        selected: selectedPaths.has(file.path)
      }))
      setNodeCache(prev => new Map(prev).set('', rootChildren))

      // Get effective permissions for all visible paths
      await updatePermissionResults(tree)
    } catch (error) {
      console.error('Failed to load file tree:', error)
    }
  }

  // Build hierarchical file tree from flat file list
  const buildFileTree = (files: any[]): FileTreeNode[] => {
    const nodeMap = new Map<string, FileTreeNode>()
    const roots: FileTreeNode[] = []

    // Create nodes for all files
    files.forEach(file => {
      const node: FileTreeNode = {
        path: file.path,
        name: file.name,
        isDirectory: file.is_directory,
        children: [],
        expanded: expandedPaths.has(file.path),
        selected: selectedPaths.has(file.path),
      }
      nodeMap.set(file.path, node)
    })

    // Build hierarchy
    files.forEach(file => {
      const node = nodeMap.get(file.path)!
      const parentPath = file.path.split('/').slice(0, -1).join('/')

      if (parentPath && nodeMap.has(parentPath)) {
        const parent = nodeMap.get(parentPath)!
        parent.children = parent.children || []
        parent.children.push(node)
      } else {
        roots.push(node)
      }
    })

    // Sort children alphabetically with directories first
    const sortNodes = (nodes: FileTreeNode[]) => {
      nodes.sort((a, b) => {
        if (a.isDirectory && !b.isDirectory) return -1
        if (!a.isDirectory && b.isDirectory) return 1
        return a.name.localeCompare(b.name)
      })
      nodes.forEach(node => {
        if (node.children) sortNodes(node.children)
      })
    }

    sortNodes(roots)
    return roots
  }

  // Update tree with children for incremental loading
  const updateTreeWithChildren = (parentPath: string, children: FileTreeNode[]) => {
    setFileTree(prevTree => {
      const newTree = [...prevTree]

      const findAndUpdate = (nodes: FileTreeNode[]): boolean => {
        for (const node of nodes) {
          if (node.path === parentPath) {
            node.children = children.map(child => ({
              path: child.path,
              name: child.name,
              isDirectory: child.isDirectory,
              children: child.isDirectory ? [] : undefined,
              expanded: expandedPaths.has(child.path),
              selected: selectedPaths.has(child.path)
            }))
            return true
          }
          if (node.children && findAndUpdate(node.children)) {
            return true
          }
        }
        return false
      }

      findAndUpdate(newTree)
      return newTree
    })
  }

  // Collect all visible paths from file tree
  const collectVisiblePaths = useCallback((nodes: FileTreeNode[], paths: string[] = []): string[] => {
    nodes.forEach(node => {
      paths.push(node.path)
      if (node.isDirectory && node.expanded && node.children) {
        collectVisiblePaths(node.children, paths)
      }
    })
    return paths
  }, [])

  // Update permission results using batch API
  const updatePermissionResults = async (tree: FileTreeNode[]) => {
    setLoadingPermissions(true)
    try {
      const visiblePaths = collectVisiblePaths(tree)
      if (visiblePaths.length > 0) {
        const results = await getBatchEffectivePermissions(workspaceId, visiblePaths)
        const resultMap = new Map<string, EffectivePermissionResult>()
        results.forEach(result => {
          resultMap.set(result.path, result)
        })
        setPermissionResults(resultMap)
      }
    } catch (error) {
      console.error('Failed to get effective permissions:', error)
    } finally {
      setLoadingPermissions(false)
    }
  }

  // Handle file tree node selection
  const handleNodeSelect = (path: string, selected: boolean) => {
    const newSelected = new Set(selectedPaths)
    if (selected) {
      newSelected.add(path)
    } else {
      newSelected.delete(path)
    }
    setSelectedPaths(newSelected)
  }

  // Handle file tree node expansion
  const handleNodeExpand = async (path: string) => {
    const newExpanded = new Set(expandedPaths)

    if (newExpanded.has(path)) {
      // Collapse
      newExpanded.delete(path)
    } else {
      // Expand and load children if needed
      newExpanded.add(path)

      // Load children for this specific path
      await loadFolderContents(path)
    }

    setExpandedPaths(newExpanded)
  }

  // Handle adding new permission
  const handleAddPermission = async (permissionData: PermissionCreate) => {
    await addPermission(workspaceId, permissionData)
    // Refresh permission results
    await updatePermissionResults(fileTree)
  }

  // Handle deleting permission
  const handleDeletePermission = async (permissionId: number) => {
    await deletePermission(permissionId)
    // Refresh permission results
    await updatePermissionResults(fileTree)
  }

  // Memoized permission list for better performance
  const sortedPermissions = useMemo(() => {
    return [...permissions].sort((a, b) => {
      // Sort by path length (more specific first), then by path
      if (a.path.length !== b.path.length) {
        return b.path.length - a.path.length
      }
      return a.path.localeCompare(b.path)
    })
  }, [permissions])

  return (
    <div className={`h-full flex ${className}`}>
      {/* Left Panel - File Tree */}
      <div className="w-1/2 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-900">File Browser</h3>
          <p className="text-sm text-gray-600 mt-1">
            Select files and folders to manage permissions
          </p>
          {loadingPermissions && (
            <div className="text-xs text-blue-600 mt-2">
              Loading permissions...
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {fileTree.length > 0 ? (
            <FileTree
              nodes={fileTree}
              onNodeSelect={handleNodeSelect}
              onNodeExpand={handleNodeExpand}
              selectedPaths={selectedPaths}
              expandedPaths={expandedPaths}
              permissionResults={permissionResults}
              loadingPaths={loadingPaths}
            />
          ) : (
            <div className="text-center text-gray-500 py-8">
              <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              <p>Loading file tree...</p>
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Permission Rules */}
      <div className="w-1/2 flex flex-col">
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Permission Rules</h3>
              <p className="text-sm text-gray-600 mt-1">
                Manage access rules for this workspace
              </p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              disabled={isLoading}
            >
              + Add Rule
            </button>
          </div>

          {selectedPaths.size > 0 && (
            <div className="mt-3 text-sm text-blue-600">
              {selectedPaths.size} path{selectedPaths.size !== 1 ? 's' : ''} selected
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          {sortedPermissions.length > 0 ? (
            <div className="space-y-3">
              {sortedPermissions.map((permission) => (
                <div
                  key={permission.id}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                          {permission.path}
                        </code>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          permission.rule_type === 'allow' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {permission.rule_type}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          permission.permission_type === 'write' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {permission.permission_type}
                        </span>
                      </div>

                      {permission.description && (
                        <p className="text-sm text-gray-600 mb-2">
                          {permission.description}
                        </p>
                      )}

                      <div className="text-xs text-gray-500">
                        ID: {permission.id} • Created: {new Date(permission.created_at).toLocaleDateString()}
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeletePermission(permission.id)}
                      className="ml-3 p-1 text-gray-400 hover:text-red-500 transition-colors"
                      title="Delete rule"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-500 py-12">
              <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <h4 className="text-lg font-medium text-gray-900 mb-2">No permission rules</h4>
              <p className="text-gray-600 mb-4">
                Add permission rules to control access to files and directories
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Add First Rule
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Add Permission Modal */}
      <AddPermissionModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleAddPermission}
        selectedPaths={Array.from(selectedPaths)}
      />
    </div>
  )
}