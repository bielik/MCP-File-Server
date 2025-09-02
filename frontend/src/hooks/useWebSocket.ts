import { useEffect, useRef, useState } from 'react';
import { wsService } from '../services/websocket.js';

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(wsService.isConnected());
  const [connectionId, setConnectionId] = useState<string | undefined>(wsService.getConnectionId());

  useEffect(() => {
    const unsubscribeStatus = wsService.on('connection-status', ({ connected }) => {
      setIsConnected(connected);
      setConnectionId(wsService.getConnectionId());
    });

    const unsubscribeError = wsService.on('connection-error', ({ error }) => {
      console.error('WebSocket connection error:', error);
    });

    const unsubscribeFailed = wsService.on('connection-failed', ({ message }) => {
      console.error('WebSocket connection failed:', message);
    });

    return () => {
      unsubscribeStatus();
      unsubscribeError();
      unsubscribeFailed();
    };
  }, []);

  const reconnect = () => {
    wsService.reconnect();
  };

  return {
    isConnected,
    connectionId,
    reconnect,
  };
}

export function useWebSocketEvent<T = any>(event: string, handler: (data: T) => void) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    const unsubscribe = wsService.on(event, (data: T) => {
      handlerRef.current(data);
    });

    return unsubscribe;
  }, [event]);
}

export function useFileSystemEvents(onFileChange?: (event: {
  type: 'added' | 'changed' | 'removed' | 'moved';
  file: string;
  data?: any;
}) => void) {
  const callbackRef = useRef(onFileChange);
  callbackRef.current = onFileChange;

  useWebSocketEvent('file-added', (data) => {
    callbackRef.current?.({ type: 'added', file: data.filePath, data });
  });

  useWebSocketEvent('file-changed', (data) => {
    callbackRef.current?.({ type: 'changed', file: data.filePath, data });
  });

  useWebSocketEvent('file-removed', (data) => {
    callbackRef.current?.({ type: 'removed', file: data.filePath, data });
  });

  useWebSocketEvent('file-moved', (data) => {
    callbackRef.current?.({ type: 'moved', file: data.sourcePath, data });
  });
}

export function useSystemStatus(onStatusChange?: (status: any) => void) {
  const [status, setStatus] = useState<any>(null);
  const callbackRef = useRef(onStatusChange);
  callbackRef.current = onStatusChange;

  useWebSocketEvent('system-status', (data) => {
    setStatus(data);
    callbackRef.current?.(data);
  });

  const requestStatus = () => {
    wsService.requestSystemStatus();
  };

  return {
    status,
    requestStatus,
  };
}