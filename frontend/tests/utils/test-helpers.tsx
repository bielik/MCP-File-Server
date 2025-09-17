/**
 * Test Helper Components and Utilities for Phase 3B Frontend Testing
 *
 * This file provides reusable components, custom render functions, and utilities
 * specifically designed for testing React components in the Phase 3B workspace system.
 *
 * For independent testers:
 * - Use customRender() instead of RTL's render() for components with context
 * - Mock providers are pre-configured with realistic state
 * - Helper components simulate user interactions realistically
 * - All utilities include TypeScript support for better test safety
 */

import React, { ReactElement, ReactNode } from 'react'
import { render, RenderOptions, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, Mock } from 'vitest'

import { TEST_CONSTANTS, TestPerformanceTimer, mockDataGenerators, TestWorkspace, TestPermission } from '../setup'

// Mock Context Providers
interface MockWorkspaceContextValue {
  workspaces: TestWorkspace[]
  activeWorkspace: TestWorkspace | null
  permissions: TestPermission[]
  selectedPaths: string[]
  isLoading: boolean
  error: string | null
  createWorkspace: Mock
  updateWorkspace: Mock
  deleteWorkspace: Mock
  activateWorkspace: Mock
  addPermission: Mock
  updatePermission: Mock
  deletePermission: Mock
  setSelectedPaths: Mock
  fetchEffectivePermissions: Mock
}

// Create mock workspace context
export const createMockWorkspaceContext = (overrides: Partial<MockWorkspaceContextValue> = {}): MockWorkspaceContextValue => {
  return {
    workspaces: [],
    activeWorkspace: null,
    permissions: [],
    selectedPaths: [],
    isLoading: false,
    error: null,
    createWorkspace: vi.fn().mockResolvedValue({ success: true }),
    updateWorkspace: vi.fn().mockResolvedValue({ success: true }),
    deleteWorkspace: vi.fn().mockResolvedValue({ success: true }),
    activateWorkspace: vi.fn().mockResolvedValue({ success: true }),
    addPermission: vi.fn().mockResolvedValue({ success: true }),
    updatePermission: vi.fn().mockResolvedValue({ success: true }),
    deletePermission: vi.fn().mockResolvedValue({ success: true }),
    setSelectedPaths: vi.fn(),
    fetchEffectivePermissions: vi.fn().mockResolvedValue({ success: true }),
    ...overrides
  }
}

// Mock WebSocket context
interface MockWebSocketContextValue {
  isConnected: boolean
  connectionState: 'connecting' | 'connected' | 'disconnected'
  lastMessage: any
  send: Mock
  subscribe: Mock
  unsubscribe: Mock
}

export const createMockWebSocketContext = (overrides: Partial<MockWebSocketContextValue> = {}): MockWebSocketContextValue => {
  return {
    isConnected: true,
    connectionState: 'connected',
    lastMessage: null,
    send: vi.fn(),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    ...overrides
  }
}

// Mock providers wrapper
interface TestProvidersProps {
  children: ReactNode
  workspaceContext?: Partial<MockWorkspaceContextValue>
  webSocketContext?: Partial<MockWebSocketContextValue>
}

export const TestProviders: React.FC<TestProvidersProps> = ({
  children,
  workspaceContext = {},
  webSocketContext = {}
}) => {
  const mockWorkspaceValue = createMockWorkspaceContext(workspaceContext)
  const mockWebSocketValue = createMockWebSocketContext(webSocketContext)

  // Mock React contexts (these would be imported from actual context files)
  const WorkspaceContext = React.createContext(mockWorkspaceValue)
  const WebSocketContext = React.createContext(mockWebSocketValue)

  return (
    <WorkspaceContext.Provider value={mockWorkspaceValue}>
      <WebSocketContext.Provider value={mockWebSocketValue}>
        {children}
      </WebSocketContext.Provider>
    </WorkspaceContext.Provider>
  )
}

// Custom render function with providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  workspaceContext?: Partial<MockWorkspaceContextValue>
  webSocketContext?: Partial<MockWebSocketContextValue>
}

export const customRender = (
  ui: ReactElement,
  options: CustomRenderOptions = {}
) => {
  const { workspaceContext, webSocketContext, ...renderOptions } = options

  const Wrapper: React.FC<{ children: ReactNode }> = ({ children }) => (
    <TestProviders
      workspaceContext={workspaceContext}
      webSocketContext={webSocketContext}
    >
      {children}
    </TestProviders>
  )

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

// User interaction helpers
export const userInteractionHelpers = {
  // Workspace management interactions
  createWorkspace: async (name: string, description?: string, shouldActivate?: boolean) => {
    const user = userEvent.setup()

    // Click create button
    const createButton = screen.getByRole('button', { name: /create workspace/i })
    await user.click(createButton)

    // Fill form
    const nameInput = screen.getByLabelText(/workspace name/i)
    await user.type(nameInput, name)

    if (description) {
      const descriptionInput = screen.getByLabelText(/description/i)
      await user.type(descriptionInput, description)
    }

    if (shouldActivate) {
      const activateCheckbox = screen.getByLabelText(/activate/i)
      await user.click(activateCheckbox)
    }

    // Submit form
    const submitButton = screen.getByRole('button', { name: /create/i })
    await user.click(submitButton)

    return { nameInput, submitButton }
  },

  activateWorkspace: async (workspaceName: string) => {
    const user = userEvent.setup()

    const workspaceCard = screen.getByText(workspaceName).closest('[data-testid*="workspace"]')
    expect(workspaceCard).toBeInTheDocument()

    const activateButton = within(workspaceCard!).getByRole('button', { name: /activate/i })
    await user.click(activateButton)

    return { workspaceCard, activateButton }
  },

  deleteWorkspace: async (workspaceName: string) => {
    const user = userEvent.setup()

    const workspaceCard = screen.getByText(workspaceName).closest('[data-testid*="workspace"]')
    expect(workspaceCard).toBeInTheDocument()

    const deleteButton = within(workspaceCard!).getByRole('button', { name: /delete/i })
    await user.click(deleteButton)

    // Confirm deletion
    const confirmButton = screen.getByRole('button', { name: /confirm/i })
    await user.click(confirmButton)

    return { workspaceCard, deleteButton, confirmButton }
  },

  // Permission management interactions
  addPermission: async (path: string, permissionType: 'read' | 'write', ruleType: 'allow' | 'deny', description?: string) => {
    const user = userEvent.setup()

    const addButton = screen.getByRole('button', { name: /add permission/i })
    await user.click(addButton)

    const pathInput = screen.getByLabelText(/path/i)
    await user.type(pathInput, path)

    const typeSelect = screen.getByLabelText(/permission type/i)
    await user.selectOptions(typeSelect, permissionType)

    const ruleSelect = screen.getByLabelText(/rule type/i)
    await user.selectOptions(ruleSelect, ruleType)

    if (description) {
      const descriptionInput = screen.getByLabelText(/description/i)
      await user.type(descriptionInput, description)
    }

    const submitButton = screen.getByRole('button', { name: /add/i })
    await user.click(submitButton)

    return { pathInput, typeSelect, ruleSelect, submitButton }
  },

  selectPaths: async (paths: string[]) => {
    const user = userEvent.setup()

    for (const path of paths) {
      const pathElement = screen.getByText(path)
      const checkbox = within(pathElement.closest('[data-testid*="file-item"]')!).getByRole('checkbox')
      await user.click(checkbox)
    }

    return paths.map(path => screen.getByText(path))
  },

  inspectPermission: async (path: string, triggerType: 'hover' | 'click' = 'hover') => {
    const user = userEvent.setup()

    const pathElement = screen.getByText(path)
    const permissionIndicator = within(pathElement.closest('[data-testid*="file-item"]')!).getByTestId('permission-indicator')

    if (triggerType === 'hover') {
      await user.hover(permissionIndicator)
    } else {
      await user.click(permissionIndicator)
    }

    // Wait for tooltip/modal to appear
    await waitFor(() => {
      expect(screen.getByTestId('permission-inspector')).toBeInTheDocument()
    })

    return { pathElement, permissionIndicator }
  }
}

// File tree test helpers
export const fileTreeHelpers = {
  // Create realistic file tree structure
  createFileTree: (paths: string[]) => {
    const tree: any = {}

    paths.forEach(path => {
      const parts = path.split('/')
      let current = tree

      parts.forEach((part, index) => {
        if (!current[part]) {
          current[part] = index === parts.length - 1 ? { isFile: true } : {}
        }
        current = current[part]
      })
    })

    return tree
  },

  // Generate large file list for performance testing
  generateLargeFileList: (count: number = 1000): string[] => {
    const files = []
    const directories = ['materials', 'projects', 'private', 'output', 'temp']
    const fileTypes = ['.md', '.txt', '.py', '.js', '.json', '.pdf', '.docx']

    for (let i = 0; i < count; i++) {
      const dir = directories[i % directories.length]
      const subdir = `subdir_${Math.floor(i / 100)}`
      const filename = `file_${i}${fileTypes[i % fileTypes.length]}`
      files.push(`${dir}/${subdir}/${filename}`)
    }

    return files
  },

  // Simulate file tree navigation
  navigateToPath: async (path: string) => {
    const user = userEvent.setup()
    const parts = path.split('/')

    for (const part of parts) {
      const folderElement = screen.getByText(part)
      await user.click(folderElement)

      // Wait for expansion
      await waitFor(() => {
        expect(folderElement.closest('[data-testid*="folder"]')).toHaveAttribute('aria-expanded', 'true')
      })
    }

    return parts
  }
}

// Performance testing utilities
export const performanceHelpers = {
  // Measure component render time
  measureRenderTime: async (renderFn: () => void): Promise<number> => {
    const timer = new TestPerformanceTimer()
    timer.start()
    renderFn()
    await waitFor(() => {
      // Wait for component to be fully rendered
      expect(document.body.firstChild).toBeInTheDocument()
    })
    return timer.end()
  },

  // Measure API response handling
  measureApiResponse: async (apiCall: () => Promise<any>): Promise<{ duration: number, result: any }> => {
    const timer = new TestPerformanceTimer()
    timer.start()
    const result = await apiCall()
    const duration = timer.end()
    return { duration, result }
  },

  // Measure workspace switching performance
  measureWorkspaceSwitch: async (fromWorkspace: string, toWorkspace: string): Promise<number> => {
    const timer = new TestPerformanceTimer()
    timer.start()

    await userInteractionHelpers.activateWorkspace(toWorkspace)

    // Wait for UI updates to complete
    await waitFor(() => {
      expect(screen.getByText(toWorkspace)).toHaveClass('active')
    }, { timeout: TEST_CONSTANTS.PERFORMANCE_THRESHOLDS.WORKSPACE_SWITCH_MS })

    return timer.end()
  },

  // Assert performance threshold
  assertPerformanceThreshold: (duration: number, threshold: number, operation: string) => {
    if (duration > threshold) {
      throw new Error(`Performance threshold exceeded for ${operation}: ${duration}ms > ${threshold}ms`)
    }
  }
}

// Mock data generators for components
export const componentMockData = {
  // Generate workspace list with various states
  generateWorkspaceList: (count: number = 5): TestWorkspace[] => {
    return Array.from({ length: count }, (_, i) => ({
      ...mockDataGenerators.workspace({
        id: i + 1,
        name: `Workspace ${i + 1}`,
        is_active: i === 0, // First workspace is active
        description: `Test workspace ${i + 1} for component testing`
      })
    }))
  },

  // Generate permission list with various rules
  generatePermissionList: (workspaceId: number, count: number = 10): TestPermission[] => {
    const paths = ['materials', 'projects', 'private', 'output', 'temp']
    const permissionTypes: ('read' | 'write')[] = ['read', 'write']
    const ruleTypes: ('allow' | 'deny')[] = ['allow', 'deny']

    return Array.from({ length: count }, (_, i) => ({
      ...mockDataGenerators.permission({
        id: i + 1,
        workspace_id: workspaceId,
        path: `${paths[i % paths.length]}/subpath_${i}`,
        permission_type: permissionTypes[i % permissionTypes.length],
        rule_type: ruleTypes[i % ruleTypes.length],
        description: `Test permission ${i + 1}`
      })
    }))
  },

  // Generate batch permission response
  generateBatchResponse: (paths: string[]) => ({
    results: paths.map((path, index) => ({
      path,
      status: index % 3 === 0 ? 'denied' : index % 3 === 1 ? 'read' : 'write',
      matchedRule: {
        id: index + 1,
        path: path.split('/')[0],
        permission_type: 'read',
        rule_type: index % 3 === 0 ? 'deny' : 'allow',
        description: `Rule for ${path.split('/')[0]}`
      }
    }))
  })
}

// Assertion helpers for component testing
export const componentAssertions = {
  // Assert workspace is displayed correctly
  assertWorkspaceDisplay: (workspace: TestWorkspace) => {
    expect(screen.getByText(workspace.name)).toBeInTheDocument()
    expect(screen.getByText(workspace.description!)).toBeInTheDocument()

    if (workspace.is_active) {
      expect(screen.getByText(workspace.name).closest('[data-testid*="workspace"]')).toHaveClass('active')
    }
  },

  // Assert permission is displayed correctly
  assertPermissionDisplay: (permission: TestPermission) => {
    expect(screen.getByText(permission.path)).toBeInTheDocument()
    expect(screen.getByText(permission.permission_type)).toBeInTheDocument()
    expect(screen.getByText(permission.rule_type)).toBeInTheDocument()
  },

  // Assert loading states
  assertLoadingState: (isLoading: boolean = true) => {
    if (isLoading) {
      expect(screen.getByTestId('loading-spinner') || screen.getByText(/loading/i)).toBeInTheDocument()
    } else {
      expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument()
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
    }
  },

  // Assert error states
  assertErrorState: (errorMessage?: string) => {
    const errorElement = screen.getByTestId('error-message') || screen.getByRole('alert')
    expect(errorElement).toBeInTheDocument()

    if (errorMessage) {
      expect(errorElement).toHaveTextContent(errorMessage)
    }
  },

  // Assert permission indicator states
  assertPermissionIndicator: (path: string, expectedStatus: 'read' | 'write' | 'denied' | 'none') => {
    const pathElement = screen.getByText(path)
    const indicator = within(pathElement.closest('[data-testid*="file-item"]')!).getByTestId('permission-indicator')

    expect(indicator).toHaveClass(`permission-${expectedStatus}`)
  }
}

// Error simulation helpers
export const errorSimulationHelpers = {
  // Simulate network errors
  simulateNetworkError: (apiCall: Mock) => {
    apiCall.mockRejectedValueOnce(new Error('Network error'))
  },

  // Simulate validation errors
  simulateValidationError: (apiCall: Mock, field: string, message: string) => {
    apiCall.mockRejectedValueOnce({
      code: 'VALIDATION_ERROR',
      message: `Validation failed for ${field}`,
      details: { [field]: message }
    })
  },

  // Simulate server errors
  simulateServerError: (apiCall: Mock) => {
    apiCall.mockRejectedValueOnce({
      code: 'INTERNAL_SERVER_ERROR',
      message: 'Internal server error',
      status: 500
    })
  },

  // Simulate permission denied
  simulatePermissionDenied: (apiCall: Mock) => {
    apiCall.mockRejectedValueOnce({
      code: 'PERMISSION_DENIED',
      message: 'Permission denied',
      status: 403
    })
  }
}

// Re-export everything from testing library for convenience
export * from '@testing-library/react'
export { customRender as render }
export { userEvent }