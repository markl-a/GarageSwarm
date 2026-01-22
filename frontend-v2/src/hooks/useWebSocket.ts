/**
 * useWebSocket Hook
 *
 * React hook for WebSocket connection management with automatic
 * cleanup on unmount and event subscription utilities.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import websocketService, {
  WebSocketConfig,
  getWebSocketUrl,
} from '../services/websocket';
import {
  ConnectionState,
  WSEventPayloadMap,
  SubscriptionChannel,
  EventHandler,
} from '../types/websocket';

// ============================================================================
// Types
// ============================================================================

export interface UseWebSocketOptions {
  /** Auto-connect on mount */
  autoConnect?: boolean;
  /** Custom WebSocket URL */
  url?: string;
  /** Authentication token */
  token?: string;
  /** Enable debug logging */
  debug?: boolean;
  /** Channels to subscribe to on connect */
  channels?: SubscriptionChannel[];
  /** Callback when connection state changes */
  onStateChange?: (state: ConnectionState) => void;
  /** Callback when an error occurs */
  onError?: (error: Error) => void;
}

export interface UseWebSocketReturn {
  /** Current connection state */
  connectionState: ConnectionState;
  /** Whether currently connected */
  isConnected: boolean;
  /** Whether currently connecting */
  isConnecting: boolean;
  /** Whether currently reconnecting */
  isReconnecting: boolean;
  /** Connect to WebSocket server */
  connect: (config?: Partial<WebSocketConfig>) => void;
  /** Disconnect from WebSocket server */
  disconnect: () => void;
  /** Reconnect to WebSocket server */
  reconnect: () => void;
  /** Subscribe to an event */
  subscribe: <E extends keyof WSEventPayloadMap>(
    event: E,
    handler: EventHandler<WSEventPayloadMap[E]>
  ) => () => void;
  /** Subscribe to channels */
  subscribeChannels: (channels: SubscriptionChannel | SubscriptionChannel[]) => void;
  /** Unsubscribe from channels */
  unsubscribeChannels: (channels: SubscriptionChannel | SubscriptionChannel[]) => void;
  /** Send a message */
  send: <T = unknown>(event: string, data?: T) => boolean;
  /** Send a message and wait for acknowledgment */
  sendWithAck: <T = unknown, R = unknown>(
    event: string,
    data?: T,
    timeout?: number
  ) => Promise<R>;
  /** Last error that occurred */
  error: Error | null;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    autoConnect = true,
    url,
    token,
    debug = false,
    channels = [],
    onStateChange,
    onError,
  } = options;

  const [connectionState, setConnectionState] = useState<ConnectionState>(
    websocketService.getConnectionState()
  );
  const [error, setError] = useState<Error | null>(null);

  // Track cleanup functions for event subscriptions
  const cleanupFnsRef = useRef<(() => void)[]>([]);
  const initialChannelsRef = useRef(channels);

  // Handle connection state changes
  useEffect(() => {
    const unsubscribe = websocketService.onStateChange((state) => {
      setConnectionState(state);
      onStateChange?.(state);
    });

    return unsubscribe;
  }, [onStateChange]);

  // Handle errors
  useEffect(() => {
    const unsubscribe = websocketService.onError((err) => {
      setError(err);
      onError?.(err);
    });

    return unsubscribe;
  }, [onError]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && websocketService.getConnectionState() === ConnectionState.DISCONNECTED) {
      websocketService.connect({
        url: url || getWebSocketUrl(),
        token,
        debug,
      });
    }

    // Subscribe to initial channels after connection
    const handleConnect = (state: ConnectionState) => {
      if (state === ConnectionState.CONNECTED && initialChannelsRef.current.length > 0) {
        websocketService.subscribe(initialChannelsRef.current);
      }
    };

    const unsubscribe = websocketService.onStateChange(handleConnect);

    // If already connected, subscribe immediately
    if (
      websocketService.getConnectionState() === ConnectionState.CONNECTED &&
      initialChannelsRef.current.length > 0
    ) {
      websocketService.subscribe(initialChannelsRef.current);
    }

    return () => {
      unsubscribe();
      // Cleanup event subscriptions on unmount
      cleanupFnsRef.current.forEach((cleanup) => cleanup());
      cleanupFnsRef.current = [];
    };
  }, [autoConnect, url, token, debug]);

  // Connect function
  const connect = useCallback(
    (config?: Partial<WebSocketConfig>) => {
      setError(null);
      websocketService.connect({
        url: url || getWebSocketUrl(),
        token,
        debug,
        ...config,
      });
    },
    [url, token, debug]
  );

  // Disconnect function
  const disconnect = useCallback(() => {
    websocketService.disconnect();
  }, []);

  // Reconnect function
  const reconnect = useCallback(() => {
    setError(null);
    websocketService.reconnect();
  }, []);

  // Subscribe to events with automatic cleanup tracking
  const subscribe = useCallback(
    <E extends keyof WSEventPayloadMap>(
      event: E,
      handler: EventHandler<WSEventPayloadMap[E]>
    ): (() => void) => {
      const unsubscribe = websocketService.on(event, handler);
      cleanupFnsRef.current.push(unsubscribe);

      return () => {
        unsubscribe();
        const index = cleanupFnsRef.current.indexOf(unsubscribe);
        if (index > -1) {
          cleanupFnsRef.current.splice(index, 1);
        }
      };
    },
    []
  );

  // Subscribe to channels
  const subscribeChannels = useCallback(
    (channelsToSubscribe: SubscriptionChannel | SubscriptionChannel[]) => {
      websocketService.subscribe(channelsToSubscribe);
    },
    []
  );

  // Unsubscribe from channels
  const unsubscribeChannels = useCallback(
    (channelsToUnsubscribe: SubscriptionChannel | SubscriptionChannel[]) => {
      websocketService.unsubscribe(channelsToUnsubscribe);
    },
    []
  );

  // Send message
  const send = useCallback(<T = unknown>(event: string, data?: T): boolean => {
    return websocketService.send(event, data);
  }, []);

  // Send message with acknowledgment
  const sendWithAck = useCallback(
    <T = unknown, R = unknown>(
      event: string,
      data?: T,
      timeout?: number
    ): Promise<R> => {
      return websocketService.sendWithAck<T, R>(event, data, timeout);
    },
    []
  );

  return {
    connectionState,
    isConnected: connectionState === ConnectionState.CONNECTED,
    isConnecting: connectionState === ConnectionState.CONNECTING,
    isReconnecting: connectionState === ConnectionState.RECONNECTING,
    connect,
    disconnect,
    reconnect,
    subscribe,
    subscribeChannels,
    unsubscribeChannels,
    send,
    sendWithAck,
    error,
  };
}

// ============================================================================
// Specialized Event Subscription Hook
// ============================================================================

/**
 * Hook for subscribing to specific WebSocket events
 * Automatically cleans up on unmount
 */
export function useWebSocketEvent<E extends keyof WSEventPayloadMap>(
  event: E,
  handler: EventHandler<WSEventPayloadMap[E]>,
  enabled = true
): void {
  const handlerRef = useRef(handler);

  // Keep handler ref up to date
  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!enabled) return;

    const unsubscribe = websocketService.on(event, (payload) => {
      handlerRef.current(payload);
    });

    return unsubscribe;
  }, [event, enabled]);
}

/**
 * Hook for subscribing to channels
 * Automatically subscribes on mount and unsubscribes on unmount
 */
export function useWebSocketChannels(
  channels: SubscriptionChannel | SubscriptionChannel[],
  enabled = true
): void {
  useEffect(() => {
    if (!enabled) return;

    const channelArray = Array.isArray(channels) ? channels : [channels];

    // Subscribe when connected
    if (websocketService.isConnected()) {
      websocketService.subscribe(channelArray);
    }

    // Also subscribe when connection is established
    const unsubscribeState = websocketService.onStateChange((state) => {
      if (state === ConnectionState.CONNECTED) {
        websocketService.subscribe(channelArray);
      }
    });

    return () => {
      unsubscribeState();
      if (websocketService.isConnected()) {
        websocketService.unsubscribe(channelArray);
      }
    };
  }, [channels, enabled]);
}

export default useWebSocket;
