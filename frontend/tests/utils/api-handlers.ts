/**
 * Mock Service Worker (MSW) API Handlers for Phase 3B Testing
 *
 * This file defines all the mock API responses for testing frontend components
 * without needing a real backend. Each handler simulates the actual API behavior
 * including success/error scenarios, validation, and realistic response times.
 *
 * For independent testers:
 * - Handlers automatically simulate realistic API delays
 * - Error scenarios are pre-configured for edge case testing
 * - Response data matches the exact schema used in production
 * - Special handlers for performance testing scenarios
 */

import { http, HttpResponse } from 'msw'
import { TEST_CONSTANTS, mockDataGenerators, TestWorkspace, TestPermission } from '../setup'

// In-memory storage for test data
let mockWorkspaces: TestWorkspace[] = []
let mockPermissions: TestPermission[] = []
let activeWorkspaceId: number | null = null

// Utility functions
const findWorkspace = (id: number) => mockWorkspaces.find(w => w.id === id)
const findPermission = (workspaceId: number, permissionId: number) =>
  mockPermissions.find(p => p.workspace_id === workspaceId && p.id === permissionId)

const getWorkspacePermissions = (workspaceId: number) =>
  mockPermissions.filter(p => p.workspace_id === workspaceId)

// Simulate realistic API delays
const simulateDelay = (minMs: number = 10, maxMs: number = 50) =>
  new Promise(resolve => setTimeout(resolve, Math.random() * (maxMs - minMs) + minMs))

// Error response helper
const createErrorResponse = (status: number, code: string, message: string, details: any = null) =>
  HttpResponse.json({ code, message, details }, { status })

export const apiHandlers = [
  // Workspace Management Endpoints

  // GET /api/workspaces - List all workspaces
  http.get('/api/workspaces', async ({ request }) => {
    await simulateDelay()

    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const pageSize = parseInt(url.searchParams.get('pageSize') || '10')

    const startIndex = (page - 1) * pageSize
    const endIndex = startIndex + pageSize
    const paginatedWorkspaces = mockWorkspaces.slice(startIndex, endIndex)

    return HttpResponse.json({
      workspaces: paginatedWorkspaces,
      total: mockWorkspaces.length,
      page,
      pageSize,
      totalPages: Math.ceil(mockWorkspaces.length / pageSize)
    })
  }),

  // POST /api/workspaces - Create workspace
  http.post('/api/workspaces', async ({ request }) => {
    await simulateDelay(20, 100) // Create operations take a bit longer

    const body = await request.json() as any

    // Validation
    if (!body.name || body.name.trim().length === 0) {
      return createErrorResponse(400, 'VALIDATION_ERROR', 'Workspace name is required')
    }

    // Check for duplicate names
    if (mockWorkspaces.some(w => w.name === body.name)) {
      return createErrorResponse(409, 'DUPLICATE_NAME', 'Workspace name must be unique')
    }

    // Create new workspace
    const newWorkspace = mockDataGenerators.workspace({
      ...body,
      id: Math.max(0, ...mockWorkspaces.map(w => w.id)) + 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      version: 1
    })

    mockWorkspaces.push(newWorkspace)

    // If this is set as active, deactivate others
    if (newWorkspace.is_active) {
      mockWorkspaces.forEach(w => {
        if (w.id !== newWorkspace.id) w.is_active = false
      })
      activeWorkspaceId = newWorkspace.id
    }

    return HttpResponse.json(newWorkspace, { status: 201 })
  }),

  // GET /api/workspaces/:id - Get workspace by ID
  http.get('/api/workspaces/:id', async ({ params }) => {
    await simulateDelay()

    const workspaceId = parseInt(params.id as string)
    const workspace = findWorkspace(workspaceId)

    if (!workspace) {
      return createErrorResponse(404, 'WORKSPACE_NOT_FOUND', `Workspace ${workspaceId} not found`)
    }

    return HttpResponse.json(workspace)
  }),

  // PUT /api/workspaces/:id - Update workspace
  http.put('/api/workspaces/:id', async ({ params, request }) => {
    await simulateDelay(20, 80)

    const workspaceId = parseInt(params.id as string)
    const workspace = findWorkspace(workspaceId)

    if (!workspace) {
      return createErrorResponse(404, 'WORKSPACE_NOT_FOUND', `Workspace ${workspaceId} not found`)
    }

    const updates = await request.json() as any

    // Validation
    if (updates.name && mockWorkspaces.some(w => w.id !== workspaceId && w.name === updates.name)) {
      return createErrorResponse(409, 'DUPLICATE_NAME', 'Workspace name must be unique')
    }

    // Apply updates
    Object.assign(workspace, {
      ...updates,
      updated_at: new Date().toISOString(),
      version: workspace.version + 1
    })

    // Handle activation change
    if (updates.is_active !== undefined) {
      if (updates.is_active) {
        // Deactivate all other workspaces
        mockWorkspaces.forEach(w => {
          if (w.id !== workspaceId) w.is_active = false
        })
        activeWorkspaceId = workspaceId
      } else if (workspace.is_active) {
        activeWorkspaceId = null
      }
    }

    return HttpResponse.json(workspace)
  }),

  // PUT /api/workspaces/:id/activate - Activate workspace
  http.put('/api/workspaces/:id/activate', async ({ params }) => {
    await simulateDelay(30, 150) // Activation takes longer due to cache rebuilding

    const workspaceId = parseInt(params.id as string)
    const workspace = findWorkspace(workspaceId)

    if (!workspace) {
      return createErrorResponse(404, 'WORKSPACE_NOT_FOUND', `Workspace ${workspaceId} not found`)
    }

    // Deactivate all workspaces
    mockWorkspaces.forEach(w => {
      w.is_active = false
      w.updated_at = new Date().toISOString()
      w.version += 1
    })

    // Activate target workspace
    workspace.is_active = true
    workspace.updated_at = new Date().toISOString()
    workspace.version += 1
    activeWorkspaceId = workspaceId

    return HttpResponse.json({ message: 'Workspace activated successfully' })
  }),

  // DELETE /api/workspaces/:id - Delete workspace
  http.delete('/api/workspaces/:id', async ({ params }) => {
    await simulateDelay(20, 100)

    const workspaceId = parseInt(params.id as string)
    const workspaceIndex = mockWorkspaces.findIndex(w => w.id === workspaceId)

    if (workspaceIndex === -1) {
      return createErrorResponse(404, 'WORKSPACE_NOT_FOUND', `Workspace ${workspaceId} not found`)
    }

    // Remove workspace and its permissions
    mockWorkspaces.splice(workspaceIndex, 1)
    mockPermissions = mockPermissions.filter(p => p.workspace_id !== workspaceId)

    // Clear active workspace if it was deleted
    if (activeWorkspaceId === workspaceId) {
      activeWorkspaceId = null
    }

    return HttpResponse.json({ message: 'Workspace deleted successfully' })
  }),

  // Permission Management Endpoints

  // GET /api/workspaces/:id/permissions - List workspace permissions
  http.get('/api/workspaces/:workspaceId/permissions', async ({ params }) => {
    await simulateDelay()

    const workspaceId = parseInt(params.workspaceId as string)

    if (!findWorkspace(workspaceId)) {
      return createErrorResponse(404, 'WORKSPACE_NOT_FOUND', `Workspace ${workspaceId} not found`)
    }

    const permissions = getWorkspacePermissions(workspaceId)
    return HttpResponse.json({ permissions })
  }),

  // POST /api/workspaces/:id/permissions - Create permission
  http.post('/api/workspaces/:workspaceId/permissions', async ({ params, request }) => {
    await simulateDelay(20, 80)

    const workspaceId = parseInt(params.workspaceId as string)

    if (!findWorkspace(workspaceId)) {
      return createErrorResponse(404, 'WORKSPACE_NOT_FOUND', `Workspace ${workspaceId} not found`)
    }

    const body = await request.json() as any

    // Validation
    if (!body.path || !body.permission_type || !body.rule_type) {
      return createErrorResponse(400, 'VALIDATION_ERROR', 'Missing required fields')
    }

    if (!['read', 'write'].includes(body.permission_type)) {
      return createErrorResponse(400, 'VALIDATION_ERROR', 'Invalid permission_type')
    }

    if (!['allow', 'deny'].includes(body.rule_type)) {
      return createErrorResponse(400, 'VALIDATION_ERROR', 'Invalid rule_type')
    }

    // Check for duplicate permission
    const existingPermission = mockPermissions.find(p =>
      p.workspace_id === workspaceId &&
      p.path === body.path &&
      p.permission_type === body.permission_type &&
      p.rule_type === body.rule_type
    )

    if (existingPermission) {
      return createErrorResponse(409, 'DUPLICATE_PERMISSION', 'Permission already exists')
    }

    // Create new permission
    const newPermission = mockDataGenerators.permission({
      ...body,
      id: Math.max(0, ...mockPermissions.map(p => p.id)) + 1,
      workspace_id: workspaceId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })

    mockPermissions.push(newPermission)
    return HttpResponse.json(newPermission, { status: 201 })
  }),

  // PUT /api/workspaces/:workspaceId/permissions/:permissionId - Update permission
  http.put('/api/workspaces/:workspaceId/permissions/:permissionId', async ({ params, request }) => {
    await simulateDelay(20, 80)

    const workspaceId = parseInt(params.workspaceId as string)
    const permissionId = parseInt(params.permissionId as string)

    const permission = findPermission(workspaceId, permissionId)

    if (!permission) {
      return createErrorResponse(404, 'PERMISSION_NOT_FOUND',
        `Permission ${permissionId} not found in workspace ${workspaceId}`)
    }

    const updates = await request.json() as any

    // Apply updates
    Object.assign(permission, {
      ...updates,
      updated_at: new Date().toISOString()
    })

    return HttpResponse.json(permission)
  }),

  // DELETE /api/workspaces/:workspaceId/permissions/:permissionId - Delete permission
  http.delete('/api/workspaces/:workspaceId/permissions/:permissionId', async ({ params }) => {
    await simulateDelay(20, 80)

    const workspaceId = parseInt(params.workspaceId as string)
    const permissionId = parseInt(params.permissionId as string)

    const permissionIndex = mockPermissions.findIndex(p =>
      p.workspace_id === workspaceId && p.id === permissionId)

    if (permissionIndex === -1) {
      return createErrorResponse(404, 'PERMISSION_NOT_FOUND',
        `Permission ${permissionId} not found in workspace ${workspaceId}`)
    }

    mockPermissions.splice(permissionIndex, 1)
    return HttpResponse.json({ message: 'Permission deleted successfully' })
  }),

  // POST /api/workspaces/:id/effective-permissions:batch - Batch permission check
  http.post('/api/workspaces/:workspaceId/effective-permissions:batch', async ({ params, request }) => {
    const workspaceId = parseInt(params.workspaceId as string)
    const body = await request.json() as any

    // Simulate variable delay based on batch size for performance testing
    const batchSize = body.paths?.length || 0
    const baseDelay = 10
    const perPathDelay = 0.3 // 0.3ms per path
    const totalDelay = Math.min(baseDelay + (batchSize * perPathDelay), 100)

    await simulateDelay(totalDelay - 5, totalDelay + 5)

    if (!findWorkspace(workspaceId)) {
      return createErrorResponse(404, 'WORKSPACE_NOT_FOUND', `Workspace ${workspaceId} not found`)
    }

    if (!body.paths || !Array.isArray(body.paths)) {
      return createErrorResponse(400, 'VALIDATION_ERROR', 'paths array is required')
    }

    const workspacePermissions = getWorkspacePermissions(workspaceId)

    // Simulate permission resolution logic
    const results = body.paths.map((path: string) => {
      // Find best matching permission rule (most specific path)
      let bestMatch: TestPermission | null = null
      let bestMatchSpecificity = -1

      for (const permission of workspacePermissions) {
        // Simple path matching - in reality this would be more sophisticated
        if (path.startsWith(permission.path)) {
          const specificity = permission.path.split('/').length
          if (specificity > bestMatchSpecificity) {
            bestMatch = permission
            bestMatchSpecificity = specificity
          }
        }
      }

      if (bestMatch) {
        let status: string
        if (bestMatch.rule_type === 'allow') {
          status = bestMatch.permission_type // 'read' or 'write'
        } else {
          status = 'denied'
        }

        return {
          path,
          status,
          matchedRule: {
            id: bestMatch.id,
            path: bestMatch.path,
            permission_type: bestMatch.permission_type,
            rule_type: bestMatch.rule_type,
            description: bestMatch.description
          }
        }
      } else {
        return {
          path,
          status: 'denied',
          matchedRule: {
            id: null,
            path: null,
            permission_type: null,
            rule_type: 'deny',
            description: 'No matching rule - default deny'
          }
        }
      }
    })

    return HttpResponse.json({ results })
  }),

  // Special handlers for error testing
  http.get('/api/workspaces/error-test', async () => {
    await simulateDelay()
    return createErrorResponse(500, 'INTERNAL_SERVER_ERROR', 'Simulated server error for testing')
  }),

  http.post('/api/workspaces/slow-response', async () => {
    await simulateDelay(1000, 2000) // Very slow response for timeout testing
    return HttpResponse.json({ message: 'Slow response for testing' })
  })
]

// Helper functions for test setup
export const setupMockData = {
  clearAll: () => {
    mockWorkspaces = []
    mockPermissions = []
    activeWorkspaceId = null
  },

  addWorkspace: (workspace: Partial<TestWorkspace> = {}) => {
    const newWorkspace = mockDataGenerators.workspace(workspace)
    mockWorkspaces.push(newWorkspace)
    return newWorkspace
  },

  addPermission: (permission: Partial<TestPermission> = {}) => {
    const newPermission = mockDataGenerators.permission(permission)
    mockPermissions.push(newPermission)
    return newPermission
  },

  createComplexScenario: () => {
    const workspace1 = setupMockData.addWorkspace({
      name: 'Development Workspace',
      is_active: true
    })

    const workspace2 = setupMockData.addWorkspace({
      name: 'Research Workspace',
      is_active: false
    })

    // Add complex permission set for workspace1
    const permissions1 = mockDataGenerators.complexPermissionSet(workspace1.id)
    permissions1.forEach(p => mockPermissions.push(p))

    // Add simple permissions for workspace2
    setupMockData.addPermission({
      workspace_id: workspace2.id,
      path: 'materials',
      permission_type: 'read',
      rule_type: 'allow'
    })

    activeWorkspaceId = workspace1.id

    return { workspace1, workspace2, permissions1 }
  }
}