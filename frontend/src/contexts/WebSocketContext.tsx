/**
 * WebSocket Context Provider
 * Ensures only one WebSocket connection exists across the entire app
 */

import React, { createContext, useContext, useCallback, useState } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'

interface WebSocketContextType {
  isConnected: boolean
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
  logs: string[]
  clearLogs: () => void
  error: string | null
}

const WebSocketContext = createContext<WebSocketContextType | null>(null)

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [logs, setLogs] = useState<string[]>([])

  // Memoize callback functions to prevent unnecessary WebSocket reconnections
  const handleMessage = useCallback((data: any) => {
    // Handle legacy activity log messages
    if (typeof data === 'string') {
      setLogs(prevLogs => [...prevLogs.slice(-49), data]) // Keep last 50 messages
    }
  }, [])

  const handleWorkspaceActivated = useCallback((data: any) => {
    setLogs(prevLogs => [...prevLogs.slice(-49), `Workspace activated: ${data.workspaceName}`])
  }, [])

  const handlePermissionsUpdated = useCallback((data: any) => {
    setLogs(prevLogs => [...prevLogs.slice(-49), `Permissions updated in workspace ${data.workspaceId}`])
  }, [])

  const { isConnected, connectionState, error } = useWebSocket({
    url: 'ws://localhost:8000/ws/ui',
    reconnectInterval: 5000, // Slower reconnection
    maxReconnectAttempts: 3, // Fewer attempts
    onMessage: handleMessage,
    onWorkspaceActivated: handleWorkspaceActivated,
    onPermissionsUpdated: handlePermissionsUpdated,
  })

  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        connectionState,
        logs,
        clearLogs,
        error,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider')
  }
  return context
}