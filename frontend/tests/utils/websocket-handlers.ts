/**
 * WebSocket Mock Handlers for Phase 3B Testing
 *
 * This file provides mock WebSocket behavior for testing real-time features
 * like workspace switching notifications, permission updates, and activity logs.
 *
 * For independent testers:
 * - WebSocket connections are automatically mocked
 * - Real-time events are simulated with realistic timing
 * - Message patterns match production WebSocket protocol
 * - Connection states and error scenarios are fully covered
 */

import { http, HttpResponse } from 'msw'

// Mock WebSocket message types
export interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}

// In-memory WebSocket connection simulation
class MockWebSocketConnection {
  private listeners: Map<string, Function[]> = new Map()
  private connectionState: 'connecting' | 'open' | 'closing' | 'closed' = 'connecting'
  private messageQueue: WebSocketMessage[] = []
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3

  constructor(private url: string) {
    // Simulate connection establishment
    setTimeout(() => {
      this.connectionState = 'open'
      this.emit('open', { type: 'connection_established' })
    }, 10)
  }

  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(callback)
  }

  off(event: string, callback?: Function): void {
    if (!callback) {
      this.listeners.delete(event)
    } else {
      const callbacks = this.listeners.get(event)
      if (callbacks) {
        const index = callbacks.indexOf(callback)
        if (index > -1) {
          callbacks.splice(index, 1)
        }
      }
    }
  }

  send(data: string): void {
    if (this.connectionState !== 'open') {
      throw new Error('WebSocket is not open')
    }

    const message: WebSocketMessage = {
      type: 'client_message',
      data: JSON.parse(data),
      timestamp: new Date().toISOString()
    }

    // Simulate server response to client messages
    setTimeout(() => {
      this.handleClientMessage(message)
    }, 5)
  }

  close(): void {
    this.connectionState = 'closing'
    setTimeout(() => {
      this.connectionState = 'closed'
      this.emit('close', { type: 'connection_closed' })
    }, 5)
  }

  private emit(event: string, data: any): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.forEach(callback => callback(data))
    }
  }

  private handleClientMessage(message: WebSocketMessage): void {
    // Simulate different server responses based on message type
    switch (message.data.type) {
      case 'ping':
        this.emitServerMessage('pong', { timestamp: new Date().toISOString() })
        break

      case 'subscribe_workspace_updates':
        this.emitServerMessage('subscription_confirmed', {
          subscription: 'workspace_updates',
          workspace_id: message.data.workspace_id
        })
        break

      case 'subscribe_permission_updates':
        this.emitServerMessage('subscription_confirmed', {
          subscription: 'permission_updates',
          workspace_id: message.data.workspace_id
        })
        break

      case 'subscribe_activity_log':
        this.emitServerMessage('subscription_confirmed', {
          subscription: 'activity_log'
        })
        break

      default:
        this.emitServerMessage('error', {
          code: 'UNKNOWN_MESSAGE_TYPE',
          message: `Unknown message type: ${message.data.type}`
        })
    }
  }

  private emitServerMessage(type: string, data: any): void {
    const message: WebSocketMessage = {
      type,
      data,
      timestamp: new Date().toISOString()
    }

    this.emit('message', {
      data: JSON.stringify(message)
    })
  }

  // Public methods to simulate server-side events
  simulateWorkspaceSwitch(fromWorkspaceId: number | null, toWorkspaceId: number): void {
    if (this.connectionState !== 'open') return

    // Simulate the sequence of events during workspace switching
    const events = [
      { type: 'workspace_deactivation_start', data: { workspace_id: fromWorkspaceId } },
      { type: 'permission_cache_clear', data: { workspace_id: fromWorkspaceId } },
      { type: 'workspace_activation_start', data: { workspace_id: toWorkspaceId } },
      { type: 'permission_cache_rebuild', data: { workspace_id: toWorkspaceId } },
      { type: 'workspace_activated', data: { workspace_id: toWorkspaceId } },
      { type: 'ui_refresh_required', data: { workspace_id: toWorkspaceId } }
    ]

    events.forEach((event, index) => {
      setTimeout(() => {
        this.emitServerMessage(event.type, event.data)
      }, index * 25) // 25ms between each event
    })
  }

  simulatePermissionUpdate(workspaceId: number, permissionId: number, action: 'created' | 'updated' | 'deleted'): void {
    if (this.connectionState !== 'open') return

    this.emitServerMessage('permission_updated', {
      workspace_id: workspaceId,
      permission_id: permissionId,
      action,
      timestamp: new Date().toISOString()
    })

    // Simulate cache invalidation
    setTimeout(() => {
      this.emitServerMessage('permission_cache_invalidated', {
        workspace_id: workspaceId
      })
    }, 10)
  }

  simulateActivityLog(activity: any): void {
    if (this.connectionState !== 'open') return

    this.emitServerMessage('activity_log', {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString(),
      ...activity
    })
  }

  simulateConnectionError(): void {
    this.connectionState = 'closed'
    this.emit('error', {
      type: 'connection_error',
      message: 'Simulated connection error'
    })

    // Simulate reconnection attempt
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => {
        this.connectionState = 'connecting'
        setTimeout(() => {
          this.connectionState = 'open'
          this.emit('open', { type: 'connection_restored' })
        }, 100)
      }, 1000 * this.reconnectAttempts) // Exponential backoff
    }
  }

  getConnectionState(): string {
    return this.connectionState
  }

  getMessageQueue(): WebSocketMessage[] {
    return [...this.messageQueue]
  }

  clearMessageQueue(): void {
    this.messageQueue = []
  }
}

// Global mock WebSocket connections
const mockConnections = new Map<string, MockWebSocketConnection>()

// Export mock WebSocket class for global usage
export class MockWebSocket extends EventTarget {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  public readyState: number
  public url: string
  private connection: MockWebSocketConnection

  constructor(url: string) {
    super()
    this.url = url
    this.readyState = MockWebSocket.CONNECTING
    this.connection = new MockWebSocketConnection(url)

    // Store connection for external control
    mockConnections.set(url, this.connection)

    // Forward connection events
    this.connection.on('open', () => {
      this.readyState = MockWebSocket.OPEN
      this.dispatchEvent(new Event('open'))
    })

    this.connection.on('message', (data: any) => {
      const event = new MessageEvent('message', { data: data.data })
      this.dispatchEvent(event)
    })

    this.connection.on('error', (error: any) => {
      const event = new Event('error')
      ;(event as any).error = error
      this.dispatchEvent(event)
    })

    this.connection.on('close', () => {
      this.readyState = MockWebSocket.CLOSED
      this.dispatchEvent(new CloseEvent('close'))
    })
  }

  send(data: string): void {
    this.connection.send(data)
  }

  close(code?: number, reason?: string): void {
    this.readyState = MockWebSocket.CLOSING
    this.connection.close()
  }

  // Test utility methods
  static getMockConnection(url: string): MockWebSocketConnection | undefined {
    return mockConnections.get(url)
  }

  static clearAllConnections(): void {
    mockConnections.clear()
  }

  static simulateWorkspaceSwitch(url: string, fromWorkspaceId: number | null, toWorkspaceId: number): void {
    const connection = mockConnections.get(url)
    if (connection) {
      connection.simulateWorkspaceSwitch(fromWorkspaceId, toWorkspaceId)
    }
  }

  static simulatePermissionUpdate(url: string, workspaceId: number, permissionId: number, action: 'created' | 'updated' | 'deleted'): void {
    const connection = mockConnections.get(url)
    if (connection) {
      connection.simulatePermissionUpdate(workspaceId, permissionId, action)
    }
  }

  static simulateActivityLog(url: string, activity: any): void {
    const connection = mockConnections.get(url)
    if (connection) {
      connection.simulateActivityLog(activity)
    }
  }

  static simulateConnectionError(url: string): void {
    const connection = mockConnections.get(url)
    if (connection) {
      connection.simulateConnectionError()
    }
  }
}

// MSW handlers for WebSocket upgrade requests
export const webSocketHandlers = [
  // WebSocket upgrade for UI connections
  http.get('/ws/ui', ({ request }) => {
    // In a real test, you might want to track these connection attempts
    return new Response(null, {
      status: 101,
      headers: {
        'Upgrade': 'websocket',
        'Connection': 'Upgrade',
        'Sec-WebSocket-Accept': 'mock-accept-key'
      }
    })
  }),

  // WebSocket upgrade for MCP connections
  http.get('/ws/mcp', ({ request }) => {
    return new Response(null, {
      status: 101,
      headers: {
        'Upgrade': 'websocket',
        'Connection': 'Upgrade',
        'Sec-WebSocket-Accept': 'mock-accept-key'
      }
    })
  })
]

// Test utilities for WebSocket testing
export const webSocketTestUtils = {
  // Create a mock WebSocket connection for testing
  createMockConnection: (url: string): MockWebSocket => {
    return new MockWebSocket(url)
  },

  // Wait for WebSocket messages
  waitForMessages: (connection: MockWebSocket, count: number, timeoutMs: number = 5000): Promise<any[]> => {
    return new Promise((resolve, reject) => {
      const messages: any[] = []
      const timeout = setTimeout(() => {
        reject(new Error(`Timeout waiting for ${count} WebSocket messages`))
      }, timeoutMs)

      const messageHandler = (event: MessageEvent) => {
        messages.push(JSON.parse(event.data))
        if (messages.length >= count) {
          clearTimeout(timeout)
          connection.removeEventListener('message', messageHandler)
          resolve(messages)
        }
      }

      connection.addEventListener('message', messageHandler)
    })
  },

  // Wait for WebSocket connection to open
  waitForConnection: (connection: MockWebSocket, timeoutMs: number = 1000): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (connection.readyState === MockWebSocket.OPEN) {
        resolve()
        return
      }

      const timeout = setTimeout(() => {
        reject(new Error('Timeout waiting for WebSocket connection'))
      }, timeoutMs)

      const openHandler = () => {
        clearTimeout(timeout)
        connection.removeEventListener('open', openHandler)
        resolve()
      }

      connection.addEventListener('open', openHandler)
    })
  },

  // Simulate common WebSocket scenarios
  scenarios: {
    workspaceSwitchSequence: (connection: MockWebSocket, fromId: number | null, toId: number) => {
      const mockConnection = MockWebSocket.getMockConnection(connection.url)
      if (mockConnection) {
        mockConnection.simulateWorkspaceSwitch(fromId, toId)
      }
    },

    permissionUpdateSequence: (connection: MockWebSocket, workspaceId: number, permissionId: number, action: 'created' | 'updated' | 'deleted') => {
      const mockConnection = MockWebSocket.getMockConnection(connection.url)
      if (mockConnection) {
        mockConnection.simulatePermissionUpdate(workspaceId, permissionId, action)
      }
    },

    connectionLoss: (connection: MockWebSocket) => {
      const mockConnection = MockWebSocket.getMockConnection(connection.url)
      if (mockConnection) {
        mockConnection.simulateConnectionError()
      }
    },

    activityFeed: (connection: MockWebSocket, activities: any[]) => {
      const mockConnection = MockWebSocket.getMockConnection(connection.url)
      if (mockConnection) {
        activities.forEach((activity, index) => {
          setTimeout(() => {
            mockConnection.simulateActivityLog(activity)
          }, index * 100)
        })
      }
    }
  }
}

// Export for global WebSocket replacement
export { MockWebSocket as WebSocket }