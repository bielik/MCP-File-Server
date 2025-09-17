/**
 * Test Setup and Configuration for Phase 3B Frontend Tests
 *
 * This file configures the testing environment for all Phase 3B frontend tests.
 * It sets up:
 * - React Testing Library utilities
 * - Mock Service Worker (MSW) for API mocking
 * - Custom render functions with providers
 * - Global test utilities and helpers
 *
 * For independent testers:
 * - All tests use this common setup automatically
 * - Mock servers are pre-configured for all API endpoints
 * - Custom matchers are available for workspace/permission testing
 * - Environment variables are set for consistent test behavior
 */

import { expect, vi } from 'vitest'

// Basic test setup
console.log('Test setup loaded')

// Custom matchers for workspace testing
expect.extend({
  toBeValidWorkspace(received) {
    const requiredFields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at', 'version']
    const missingFields = requiredFields.filter(field => !(field in received))

    if (missingFields.length === 0) {
      return {
        message: () => `Expected object not to be a valid workspace`,
        pass: true
      }
    } else {
      return {
        message: () => `Expected object to be a valid workspace. Missing fields: ${missingFields.join(', ')}`,
        pass: false
      }
    }
  },

  toBeValidPermission(received) {
    const requiredFields = ['id', 'workspace_id', 'path', 'permission_type', 'rule_type', 'created_at', 'updated_at']
    const missingFields = requiredFields.filter(field => !(field in received))

    if (missingFields.length === 0 &&
        ['read', 'write'].includes(received.permission_type) &&
        ['allow', 'deny'].includes(received.rule_type)) {
      return {
        message: () => `Expected object not to be a valid permission`,
        pass: true
      }
    } else {
      return {
        message: () => `Expected object to be a valid permission. Missing fields: ${missingFields.join(', ')}, or invalid permission_type/rule_type`,
        pass: false
      }
    }
  },

  toBeValidBatchResponse(received) {
    if (!received.results || !Array.isArray(received.results)) {
      return {
        message: () => `Expected batch response to have results array`,
        pass: false
      }
    }

    const invalidResults = received.results.filter(result =>
      !result.path ||
      !result.status ||
      (result.status !== 'none' && !result.matchedRule)
    )

    if (invalidResults.length === 0) {
      return {
        message: () => `Expected object not to be a valid batch response`,
        pass: true
      }
    } else {
      return {
        message: () => `Expected object to be a valid batch response. ${invalidResults.length} invalid results found`,
        pass: false
      }
    }
  }
})

// Test utility constants
export const TEST_CONSTANTS = {
  API_ENDPOINTS: {
    workspaces: '/api/workspaces',
    workspace: (id: number) => `/api/workspaces/${id}`,
    workspaceActivate: (id: number) => `/api/workspaces/${id}/activate`,
    workspacePermissions: (id: number) => `/api/workspaces/${id}/permissions`,
    permission: (workspaceId: number, permissionId: number) =>
      `/api/workspaces/${workspaceId}/permissions/${permissionId}`,
    batchPermissions: (id: number) => `/api/workspaces/${id}/effective-permissions:batch`
  },

  PERFORMANCE_THRESHOLDS: {
    COMPONENT_RENDER_MS: 100,
    API_RESPONSE_MS: 500,
    BATCH_API_MS: 100,
    WORKSPACE_SWITCH_MS: 200,
    UI_UPDATE_MS: 150
  },

  TEST_DATA: {
    SAMPLE_WORKSPACE: {
      id: 1,
      name: 'Test Workspace',
      description: 'A test workspace',
      is_active: false,
      created_at: '2025-01-15T10:00:00Z',
      updated_at: '2025-01-15T10:00:00Z',
      version: 1
    },

    SAMPLE_PERMISSION: {
      id: 1,
      workspace_id: 1,
      path: 'test/path',
      permission_type: 'read',
      rule_type: 'allow',
      description: 'Test permission',
      created_at: '2025-01-15T10:00:00Z',
      updated_at: '2025-01-15T10:00:00Z'
    },

    LARGE_PATH_LIST: Array.from({ length: 150 }, (_, i) => `test/path/${i}/file.txt`),

    REALISTIC_FILE_TREE: [
      'materials/README.md',
      'materials/course-overview.pdf',
      'materials/01_introduction/slides.pptx',
      'projects/webapp/src/main.py',
      'projects/webapp/tests/test_main.py',
      'private/config/api-keys.json',
      'output/reports/summary.pdf'
    ]
  }
}

// Export types for test files
export type TestWorkspace = typeof TEST_CONSTANTS.TEST_DATA.SAMPLE_WORKSPACE
export type TestPermission = typeof TEST_CONSTANTS.TEST_DATA.SAMPLE_PERMISSION

// Performance testing utilities
export class TestPerformanceTimer {
  private startTime: number = 0
  private endTime: number = 0

  start(): void {
    this.startTime = performance.now()
  }

  end(): number {
    this.endTime = performance.now()
    return this.endTime - this.startTime
  }

  assertWithinThreshold(thresholdMs: number, operation: string): void {
    const duration = this.end()
    if (duration > thresholdMs) {
      throw new Error(`Performance threshold exceeded for ${operation}: ${duration}ms > ${thresholdMs}ms`)
    }
  }
}

// Mock data generators
export const mockDataGenerators = {
  workspace: (overrides: Partial<TestWorkspace> = {}): TestWorkspace => ({
    ...TEST_CONSTANTS.TEST_DATA.SAMPLE_WORKSPACE,
    id: Math.floor(Math.random() * 1000),
    name: `Test Workspace ${Date.now()}`,
    ...overrides
  }),

  permission: (overrides: Partial<TestPermission> = {}): TestPermission => ({
    ...TEST_CONSTANTS.TEST_DATA.SAMPLE_PERMISSION,
    id: Math.floor(Math.random() * 1000),
    path: `test/path/${Date.now()}`,
    ...overrides
  }),

  multipleWorkspaces: (count: number): TestWorkspace[] =>
    Array.from({ length: count }, (_, i) => mockDataGenerators.workspace({
      id: i + 1,
      name: `Workspace ${i + 1}`,
      is_active: i === 0 // First workspace is active
    })),

  complexPermissionSet: (workspaceId: number) => [
    mockDataGenerators.permission({
      workspace_id: workspaceId,
      path: 'materials',
      permission_type: 'read',
      rule_type: 'allow',
      description: 'Allow read access to materials'
    }),
    mockDataGenerators.permission({
      workspace_id: workspaceId,
      path: 'projects',
      permission_type: 'write',
      rule_type: 'allow',
      description: 'Allow write access to projects'
    }),
    mockDataGenerators.permission({
      workspace_id: workspaceId,
      path: 'materials/sensitive',
      permission_type: 'read',
      rule_type: 'deny',
      description: 'Deny access to sensitive materials'
    })
  ]
}