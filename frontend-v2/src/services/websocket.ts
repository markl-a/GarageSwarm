/**
 * WebSocket Service for GarageSwarm
 *
 * Provides Socket.IO client with connection management, auto-reconnect,
 * event subscription system, and heartbeat functionality.
 */

import { io, Socket } from 'socket.io-client';
import {
  ConnectionState,
  WS_EVENTS,
  WSEventPayloadMap,
  SubscriptionChannel,
  EventHandler,
} from '../types/websocket';

// ============================================================================
// Configuration
// ============================================================================

export interface WebSocketConfig {
  /** WebSocket server URL */
  url: string;
  /** Authentication token */
  token?: string;
  /** Enable auto-reconnect */
  autoReconnect?: boolean;
  /** Maximum reconnect attempts */
  maxReconnectAttempts?: number;
  /** Initial reconnect delay in ms */
  reconnectDelay?: number;
  /** Maximum reconnect delay in ms */
  maxReconnectDelay?: number;
  /** Reconnect delay multiplier for exponential backoff */
  reconnectDelayMultiplier?: number;
  /** Heartbeat interval in ms */
  heartbeatInterval?: number;
  /** Connection timeout in ms */
  connectionTimeout?: number;
  /** Enable debug logging */
  debug?: boolean;
}

const DEFAULT_CONFIG: Required<Omit<WebSocketConfig, 'url' | 'token'>> = {
  autoReconnect: true,
  maxReconnectAttempts: 10,
  reconnectDelay: 1000,
  maxReconnectDelay: 30000,
  reconnectDelayMultiplier: 2,
  heartbeatInterval: 30000,
  connectionTimeout: 10000,
  debug: false,
};

// ============================================================================
// Event Emitter for Connection State
// ============================================================================

type ConnectionStateListener = (state: ConnectionState) => void;
type ErrorListener = (error: Error) => void;

interface ConnectionEvents {
  stateChange: Set<ConnectionStateListener>;
  error: Set<ErrorListener>;
}

// ============================================================================
// WebSocket Service Class
// ============================================================================

class WebSocketService {
  private socket: Socket | null = null;
  private config: Required<WebSocketConfig> | null = null;
  private connectionState: ConnectionState = ConnectionState.DISCONNECTED;
  private reconnectAttempts = 0;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private lastPongTime: number = 0;

  // Event listeners
  private connectionListeners: ConnectionEvents = {
    stateChange: new Set(),
    error: new Set(),
  };

  // Event handlers map: event -> Set of handlers
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();

  // Subscribed channels
  private subscribedChannels: Set<SubscriptionChannel> = new Set();

  // ============================================================================
  // Connection Management
  // ============================================================================

  /**
   * Initialize and connect to the WebSocket server
   */
  connect(config: WebSocketConfig): void {
    if (this.socket?.connected) {
      this.log('Already connected');
      return;
    }

    this.config = {
      ...DEFAULT_CONFIG,
      ...config,
    } as Required<WebSocketConfig>;

    this.setConnectionState(ConnectionState.CONNECTING);

    this.socket = io(this.config.url, {
      auth: this.config.token ? { token: this.config.token } : undefined,
      transports: ['websocket', 'polling'],
      timeout: this.config.connectionTimeout,
      autoConnect: true,
      reconnection: false, // We handle reconnection manually for exponential backoff
    });

    this.setupSocketListeners();
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.stopHeartbeat();
    this.clearReconnectTimeout();
    this.reconnectAttempts = 0;

    if (this.socket) {
      this.socket.removeAllListeners();
      this.socket.disconnect();
      this.socket = null;
    }

    this.setConnectionState(ConnectionState.DISCONNECTED);
    this.log('Disconnected');
  }

  /**
   * Reconnect to the WebSocket server
   */
  reconnect(): void {
    this.disconnect();
    if (this.config) {
      this.connect(this.config);
    }
  }

  /**
   * Get current connection state
   */
  getConnectionState(): ConnectionState {
    return this.connectionState;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connectionState === ConnectionState.CONNECTED;
  }

  // ============================================================================
  // Socket Event Listeners
  // ============================================================================

  private setupSocketListeners(): void {
    if (!this.socket) return;

    this.socket.on(WS_EVENTS.CONNECT, () => {
      this.log('Connected');
      this.reconnectAttempts = 0;
      this.setConnectionState(ConnectionState.CONNECTED);
      this.startHeartbeat();
      this.resubscribeChannels();
    });

    this.socket.on(WS_EVENTS.DISCONNECT, (reason) => {
      this.log(`Disconnected: ${reason}`);
      this.stopHeartbeat();

      if (reason === 'io server disconnect') {
        // Server initiated disconnect, don't auto-reconnect
        this.setConnectionState(ConnectionState.DISCONNECTED);
      } else if (this.config?.autoReconnect) {
        this.scheduleReconnect();
      } else {
        this.setConnectionState(ConnectionState.DISCONNECTED);
      }
    });

    this.socket.on(WS_EVENTS.CONNECT_ERROR, (error) => {
      this.log(`Connection error: ${error.message}`);
      this.emitError(new Error(`Connection error: ${error.message}`));

      if (this.config?.autoReconnect) {
        this.scheduleReconnect();
      } else {
        this.setConnectionState(ConnectionState.DISCONNECTED);
      }
    });

    this.socket.on(WS_EVENTS.PONG, () => {
      this.lastPongTime = Date.now();
      this.log('Pong received');
    });

    // Forward all registered events to handlers
    this.setupEventForwarding();
  }

  private setupEventForwarding(): void {
    if (!this.socket) return;

    // List of all events we want to forward
    const eventsToForward = [
      // Task events
      WS_EVENTS.TASK_CREATED,
      WS_EVENTS.TASK_UPDATED,
      WS_EVENTS.TASK_DELETED,
      WS_EVENTS.TASK_STATUS_CHANGED,
      WS_EVENTS.TASK_PROGRESS,
      WS_EVENTS.TASK_COMPLETED,
      WS_EVENTS.TASK_FAILED,

      // Worker events
      WS_EVENTS.WORKER_REGISTERED,
      WS_EVENTS.WORKER_UPDATED,
      WS_EVENTS.WORKER_DELETED,
      WS_EVENTS.WORKER_STATUS_CHANGED,
      WS_EVENTS.WORKER_METRICS,
      WS_EVENTS.WORKER_HEARTBEAT,

      // Workflow events
      WS_EVENTS.WORKFLOW_CREATED,
      WS_EVENTS.WORKFLOW_UPDATED,
      WS_EVENTS.WORKFLOW_DELETED,
      WS_EVENTS.WORKFLOW_STATUS_CHANGED,
      WS_EVENTS.WORKFLOW_NODE_UPDATED,
      WS_EVENTS.WORKFLOW_REVIEW_REQUESTED,
      WS_EVENTS.WORKFLOW_COMPLETED,
      WS_EVENTS.WORKFLOW_FAILED,

      // Notification events
      WS_EVENTS.NOTIFICATION,
      WS_EVENTS.NOTIFICATION_READ,
      WS_EVENTS.NOTIFICATION_CLEAR,
    ];

    eventsToForward.forEach((event) => {
      this.socket?.on(event, (payload: unknown) => {
        this.log(`Event received: ${event}`, payload);
        this.notifyHandlers(event, payload);
      });
    });
  }

  // ============================================================================
  // Reconnection Logic
  // ============================================================================

  private scheduleReconnect(): void {
    if (!this.config) return;

    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.log('Max reconnect attempts reached');
      this.setConnectionState(ConnectionState.DISCONNECTED);
      this.emitError(new Error('Max reconnection attempts reached'));
      return;
    }

    this.setConnectionState(ConnectionState.RECONNECTING);
    this.reconnectAttempts++;

    // Calculate delay with exponential backoff
    const delay = Math.min(
      this.config.reconnectDelay *
        Math.pow(this.config.reconnectDelayMultiplier, this.reconnectAttempts - 1),
      this.config.maxReconnectDelay
    );

    this.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);

    this.clearReconnectTimeout();
    this.reconnectTimeout = setTimeout(() => {
      if (this.config) {
        this.log(`Reconnect attempt ${this.reconnectAttempts}`);
        this.connect(this.config);
      }
    }, delay);
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  // ============================================================================
  // Heartbeat
  // ============================================================================

  private startHeartbeat(): void {
    if (!this.config || !this.socket) return;

    this.stopHeartbeat();
    this.lastPongTime = Date.now();

    this.heartbeatTimer = setInterval(() => {
      if (!this.socket?.connected) {
        this.stopHeartbeat();
        return;
      }

      // Check if we missed pongs
      const timeSinceLastPong = Date.now() - this.lastPongTime;
      if (timeSinceLastPong > this.config!.heartbeatInterval * 2) {
        this.log('Heartbeat timeout, reconnecting');
        this.scheduleReconnect();
        return;
      }

      this.socket.emit(WS_EVENTS.PING);
      this.log('Ping sent');
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  // ============================================================================
  // Event Subscription
  // ============================================================================

  /**
   * Subscribe to a WebSocket event
   */
  on<E extends keyof WSEventPayloadMap>(
    event: E,
    handler: EventHandler<WSEventPayloadMap[E]>
  ): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }

    const handlers = this.eventHandlers.get(event)!;
    handlers.add(handler as EventHandler);

    this.log(`Handler added for event: ${event}`);

    // Return unsubscribe function
    return () => {
      handlers.delete(handler as EventHandler);
      this.log(`Handler removed for event: ${event}`);
    };
  }

  /**
   * Unsubscribe from a WebSocket event
   */
  off<E extends keyof WSEventPayloadMap>(
    event: E,
    handler?: EventHandler<WSEventPayloadMap[E]>
  ): void {
    if (handler) {
      const handlers = this.eventHandlers.get(event);
      if (handlers) {
        handlers.delete(handler as EventHandler);
      }
    } else {
      this.eventHandlers.delete(event);
    }
  }

  /**
   * Subscribe once to a WebSocket event
   */
  once<E extends keyof WSEventPayloadMap>(
    event: E,
    handler: EventHandler<WSEventPayloadMap[E]>
  ): () => void {
    const wrappedHandler = (payload: WSEventPayloadMap[E]) => {
      this.off(event, wrappedHandler);
      handler(payload);
    };

    return this.on(event, wrappedHandler);
  }

  private notifyHandlers(event: string, payload: unknown): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(payload);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  // ============================================================================
  // Channel Subscription
  // ============================================================================

  /**
   * Subscribe to channels for receiving updates
   */
  subscribe(channels: SubscriptionChannel | SubscriptionChannel[]): void {
    const channelArray = Array.isArray(channels) ? channels : [channels];

    channelArray.forEach((channel) => {
      this.subscribedChannels.add(channel);
    });

    if (this.socket?.connected) {
      this.socket.emit(WS_EVENTS.SUBSCRIBE, { channels: channelArray });
      this.log(`Subscribed to channels: ${channelArray.join(', ')}`);
    }
  }

  /**
   * Unsubscribe from channels
   */
  unsubscribe(channels: SubscriptionChannel | SubscriptionChannel[]): void {
    const channelArray = Array.isArray(channels) ? channels : [channels];

    channelArray.forEach((channel) => {
      this.subscribedChannels.delete(channel);
    });

    if (this.socket?.connected) {
      this.socket.emit(WS_EVENTS.UNSUBSCRIBE, { channels: channelArray });
      this.log(`Unsubscribed from channels: ${channelArray.join(', ')}`);
    }
  }

  /**
   * Get currently subscribed channels
   */
  getSubscribedChannels(): SubscriptionChannel[] {
    return Array.from(this.subscribedChannels);
  }

  private resubscribeChannels(): void {
    if (this.subscribedChannels.size > 0 && this.socket?.connected) {
      const channels = Array.from(this.subscribedChannels);
      this.socket.emit(WS_EVENTS.SUBSCRIBE, { channels });
      this.log(`Resubscribed to channels: ${channels.join(', ')}`);
    }
  }

  // ============================================================================
  // Message Sending
  // ============================================================================

  /**
   * Send a message through the WebSocket
   */
  send<T = unknown>(event: string, data?: T): boolean {
    if (!this.socket?.connected) {
      this.log('Cannot send message: not connected');
      return false;
    }

    this.socket.emit(event, data);
    this.log(`Message sent: ${event}`, data);
    return true;
  }

  /**
   * Send a message and wait for acknowledgment
   */
  sendWithAck<T = unknown, R = unknown>(
    event: string,
    data?: T,
    timeout = 5000
  ): Promise<R> {
    return new Promise((resolve, reject) => {
      if (!this.socket?.connected) {
        reject(new Error('Not connected'));
        return;
      }

      const timeoutId = setTimeout(() => {
        reject(new Error(`Timeout waiting for acknowledgment: ${event}`));
      }, timeout);

      this.socket.emit(event, data, (response: R) => {
        clearTimeout(timeoutId);
        resolve(response);
      });
    });
  }

  // ============================================================================
  // Connection State Events
  // ============================================================================

  /**
   * Listen for connection state changes
   */
  onStateChange(listener: ConnectionStateListener): () => void {
    this.connectionListeners.stateChange.add(listener);
    return () => {
      this.connectionListeners.stateChange.delete(listener);
    };
  }

  /**
   * Listen for connection errors
   */
  onError(listener: ErrorListener): () => void {
    this.connectionListeners.error.add(listener);
    return () => {
      this.connectionListeners.error.delete(listener);
    };
  }

  private setConnectionState(state: ConnectionState): void {
    if (this.connectionState !== state) {
      this.connectionState = state;
      this.connectionListeners.stateChange.forEach((listener) => {
        try {
          listener(state);
        } catch (error) {
          console.error('Error in state change listener:', error);
        }
      });
    }
  }

  private emitError(error: Error): void {
    this.connectionListeners.error.forEach((listener) => {
      try {
        listener(error);
      } catch (err) {
        console.error('Error in error listener:', err);
      }
    });
  }

  // ============================================================================
  // Utilities
  // ============================================================================

  private log(message: string, data?: unknown): void {
    if (this.config?.debug) {
      if (data !== undefined) {
        console.log(`[WebSocket] ${message}`, data);
      } else {
        console.log(`[WebSocket] ${message}`);
      }
    }
  }

  /**
   * Update authentication token
   */
  updateToken(token: string): void {
    if (this.config) {
      this.config.token = token;
    }

    if (this.socket?.connected) {
      // Reconnect with new token
      this.reconnect();
    }
  }

  /**
   * Get connection statistics
   */
  getStats(): {
    connectionState: ConnectionState;
    reconnectAttempts: number;
    subscribedChannels: number;
    registeredEvents: number;
    lastPongTime: number;
  } {
    return {
      connectionState: this.connectionState,
      reconnectAttempts: this.reconnectAttempts,
      subscribedChannels: this.subscribedChannels.size,
      registeredEvents: this.eventHandlers.size,
      lastPongTime: this.lastPongTime,
    };
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

export const websocketService = new WebSocketService();

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get WebSocket URL based on environment
 */
export function getWebSocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = import.meta.env.VITE_WS_HOST || window.location.host;
  const path = import.meta.env.VITE_WS_PATH || '/ws';

  // For development, use the API URL
  if (import.meta.env.DEV) {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
    return apiUrl.replace(/^http/, 'ws');
  }

  return `${protocol}//${host}${path}`;
}

/**
 * Create a WebSocket connection with default configuration
 */
export function createWebSocketConnection(token?: string): void {
  websocketService.connect({
    url: getWebSocketUrl(),
    token,
    debug: import.meta.env.DEV,
  });
}

export default websocketService;
