import { io, Socket } from 'socket.io-client';
// import { WebSocketMessage } from '../types/index.js'; // Unused for now

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  constructor() {
    this.connect();
  }

  private connect(): void {
    const wsUrl = 'http://localhost:3001';
    
    this.socket = io(wsUrl, {
      transports: ['websocket', 'polling'],
      upgrade: true,
      rememberUpgrade: true,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connection-status', { connected: true });
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.emit('connection-status', { connected: false, reason });
      
      if (reason === 'io server disconnect') {
        // Server initiated disconnect, try to reconnect
        this.handleReconnect();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.emit('connection-error', { error: error.message });
      this.handleReconnect();
    });

    // File system events
    this.socket.on('file-added', (data) => {
      this.emit('file-added', data);
    });

    this.socket.on('file-changed', (data) => {
      this.emit('file-changed', data);
    });

    this.socket.on('file-removed', (data) => {
      this.emit('file-removed', data);
    });

    this.socket.on('file-moved', (data) => {
      this.emit('file-moved', data);
    });

    // Permission events
    this.socket.on('permission-changed', (data) => {
      this.emit('permission-changed', data);
    });

    // System events
    this.socket.on('system-status', (data) => {
      this.emit('system-status', data);
    });

    // Search events
    this.socket.on('search-completed', (data) => {
      this.emit('search-completed', data);
    });

    this.socket.on('indexing-progress', (data) => {
      this.emit('indexing-progress', data);
    });
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('connection-failed', { message: 'Failed to reconnect after multiple attempts' });
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      if (this.socket) {
        this.socket.connect();
      }
    }, delay);
  }

  // Event subscription methods
  public on(event: string, callback: (data: any) => void): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    
    this.listeners.get(event)!.add(callback);

    // Return unsubscribe function
    return () => {
      const eventListeners = this.listeners.get(event);
      if (eventListeners) {
        eventListeners.delete(callback);
        if (eventListeners.size === 0) {
          this.listeners.delete(event);
        }
      }
    };
  }

  private emit(event: string, data: any): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in WebSocket event listener for ${event}:`, error);
        }
      });
    }
  }

  // Client-to-server events
  public subscribeToFileChanges(paths: string[]): void {
    if (this.socket?.connected) {
      this.socket.emit('subscribe-file-changes', { paths });
    }
  }

  public unsubscribeFromFileChanges(paths: string[]): void {
    if (this.socket?.connected) {
      this.socket.emit('unsubscribe-file-changes', { paths });
    }
  }

  public requestSystemStatus(): void {
    if (this.socket?.connected) {
      this.socket.emit('request-system-status');
    }
  }

  public startFileIndexing(): void {
    if (this.socket?.connected) {
      this.socket.emit('start-indexing');
    }
  }

  // Connection management
  public isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  public getConnectionId(): string | undefined {
    return this.socket?.id;
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.listeners.clear();
  }

  public reconnect(): void {
    this.disconnect();
    this.reconnectAttempts = 0;
    this.connect();
  }

  // Utility methods for React hooks
  public createSubscription(event: string, callback: (data: any) => void): () => void {
    return this.on(event, callback);
  }
}

// Export singleton instance
export const wsService = new WebSocketService();
export default wsService;