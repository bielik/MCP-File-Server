/**
 * Enhanced WebSocket hook with workspace event handling
 * Phase 3B: Advanced UI & Full Workspace Experience
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import type { WebSocketMessage, WorkspaceActivatedMessage, PermissionsUpdatedMessage } from '../types/workspace'
import { useWorkspaceStore } from '../store/workspaceStore'

interface UseWebSocketOptions {
  url: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onMessage?: (data: any) => void
  onWorkspaceActivated?: (data: WorkspaceActivatedMessage['data']) => void
  onPermissionsUpdated?: (data: PermissionsUpdatedMessage['data']) => void
}

interface UseWebSocketReturn {
  isConnected: boolean
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
  send: (message: any) => void
  lastMessage: any
  error: string | null
}

export function useWebSocket({
  url,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
  onMessage,
  onWorkspaceActivated,
  onPermissionsUpdated,
}: UseWebSocketOptions): UseWebSocketReturn {
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<NodeJS.Timeout>()
  const shouldReconnect = useRef(true)

  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'reconnecting'>('disconnected')
  const [lastMessage, setLastMessage] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  // Get store actions for workspace updates
  const { fetchWorkspaces, fetchPermissions, activeWorkspace } = useWorkspaceStore()

  // Use refs to avoid dependency cycles in useCallback
  const fetchWorkspacesRef = useRef(fetchWorkspaces)
  const fetchPermissionsRef = useRef(fetchPermissions)
  fetchWorkspacesRef.current = fetchWorkspaces
  fetchPermissionsRef.current = fetchPermissions

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return
    }

    setConnectionState('connecting')
    setError(null)

    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        console.log(`WebSocket connected to ${url}`)
        setConnectionState('connected')
        reconnectAttempts.current = 0
        setError(null)

        // Send a simple test message to verify connection
        ws.current?.send('Hello from UI!')
      }

      ws.current.onmessage = (event) => {
        let messageData: any

        try {
          // Try to parse as JSON first (structured messages)
          messageData = JSON.parse(event.data)
        } catch {
          // Fall back to plain text (legacy activity logs)
          messageData = event.data
        }

        setLastMessage(messageData)

        // Handle structured WebSocket messages
        if (typeof messageData === 'object' && messageData.type) {
          const message = messageData as WebSocketMessage

          switch (message.type) {
            case 'workspace_activated':
              console.log('Workspace activated:', message.data)
              // Refresh workspace list and fetch new permissions
              fetchWorkspacesRef.current()
              if (onWorkspaceActivated) {
                onWorkspaceActivated(message.data)
              }
              break

            case 'permissions_updated':
              console.log('Permissions updated:', message.data)
              // Refresh permissions for the affected workspace
              const currentActiveWorkspace = activeWorkspace
              if (currentActiveWorkspace && message.data.workspaceId === currentActiveWorkspace.id) {
                fetchPermissionsRef.current(currentActiveWorkspace.id)
              }
              if (onPermissionsUpdated) {
                onPermissionsUpdated(message.data)
              }
              break

            case 'cache_cleared':
              console.log('Permission cache cleared')
              // Refresh current workspace permissions
              const currentActive = activeWorkspace
              if (currentActive) {
                fetchPermissionsRef.current(currentActive.id)
              }
              break

            default:
              console.log('Unknown WebSocket message type:', message.type)
          }
        }

        // Call custom message handler
        if (onMessage) {
          onMessage(messageData)
        }
      }

      ws.current.onclose = (event) => {
        console.log(`WebSocket disconnected: ${event.code} ${event.reason}`)
        setConnectionState('disconnected')

        // Only attempt to reconnect if it wasn't a clean close and we should reconnect
        if (shouldReconnect.current && event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          attemptReconnect()
        }
      }

      ws.current.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('WebSocket connection error')
        setConnectionState('disconnected')
      }

    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      setError('Failed to create WebSocket connection')
      setConnectionState('disconnected')
    }
  }, [url, onMessage, onWorkspaceActivated, onPermissionsUpdated, maxReconnectAttempts])

  const attemptReconnect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.log('Max reconnection attempts reached')
      setError('Max reconnection attempts reached')
      return
    }

    reconnectAttempts.current++
    setConnectionState('reconnecting')

    console.log(`Attempting to reconnect (${reconnectAttempts.current}/${maxReconnectAttempts})...`)

    reconnectTimer.current = setTimeout(() => {
      connect()
    }, reconnectInterval)
  }, [connect, maxReconnectAttempts, reconnectInterval])

  const disconnect = useCallback(() => {
    shouldReconnect.current = false

    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
    }

    if (ws.current) {
      ws.current.close(1000, 'Client disconnecting')
      ws.current = null
    }

    setConnectionState('disconnected')
  }, [])

  const send = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message)
      ws.current.send(messageStr)
    } else {
      console.warn('WebSocket is not connected. Cannot send message:', message)
    }
  }, [])

  // Connect on mount
  useEffect(() => {
    shouldReconnect.current = true
    connect()

    // Cleanup on unmount
    return () => {
      disconnect()
    }
  }, [])

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
      }
    }
  }, [])

  return {
    isConnected: connectionState === 'connected',
    connectionState,
    send,
    lastMessage,
    error,
  }
}

// Convenience hook for UI WebSocket connection
export function useUIWebSocket() {
  const [logs, setLogs] = useState<string[]>([])

  const { isConnected, connectionState, error } = useWebSocket({
    url: 'ws://localhost:8000/ws/ui',
    reconnectInterval: 5000, // Slower reconnection
    maxReconnectAttempts: 3, // Fewer attempts
    onMessage: (data) => {
      // Handle legacy activity log messages
      if (typeof data === 'string') {
        setLogs(prevLogs => [...prevLogs.slice(-49), data]) // Keep last 50 messages
      }
    },
    onWorkspaceActivated: (data) => {
      setLogs(prevLogs => [...prevLogs.slice(-49), `Workspace activated: ${data.workspaceName}`])
    },
    onPermissionsUpdated: (data) => {
      setLogs(prevLogs => [...prevLogs.slice(-49), `Permissions updated in workspace ${data.workspaceId}`])
    },
  })

  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  return {
    isConnected,
    connectionState,
    logs,
    clearLogs,
    error,
  }
}