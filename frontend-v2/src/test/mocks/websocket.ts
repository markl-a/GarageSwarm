/**
 * WebSocket Mock for Testing
 *
 * Provides a mock WebSocket implementation for testing WebSocket-based features.
 */

import { vi } from 'vitest';

// =============================================================================
// Types
// =============================================================================

export interface MockWebSocketMessage {
  type: string;
  payload: unknown;
}

export interface MockWebSocketOptions {
  autoConnect?: boolean;
  connectionDelay?: number;
}

// =============================================================================
// Mock WebSocket Class
// =============================================================================

export class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readonly CONNECTING = 0;
  readonly OPEN = 1;
  readonly CLOSING = 2;
  readonly CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  protocol: string = '';
  extensions: string = '';
  bufferedAmount: number = 0;
  binaryType: BinaryType = 'blob';

  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  private messageQueue: MockWebSocketMessage[] = [];
  private closeReason: { code: number; reason: string } | null = null;
  private connectionDelay: number;
  private shouldAutoConnect: boolean;

  constructor(url: string, _protocols?: string | string[]) {
    this.url = url;
    this.shouldAutoConnect = true;
    this.connectionDelay = 0;

    if (this.shouldAutoConnect) {
      this.simulateOpen();
    }
  }

  simulateOpen(delay?: number): void {
    const connectDelay = delay ?? this.connectionDelay;

    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, connectDelay);
  }

  simulateMessage(data: unknown): void {
    if (this.readyState !== MockWebSocket.OPEN) {
      return;
    }

    const messageData = typeof data === 'string' ? data : JSON.stringify(data);

    if (this.onmessage) {
      this.onmessage(
        new MessageEvent('message', {
          data: messageData,
          origin: this.url,
        })
      );
    }
  }

  simulateError(error?: Error): void {
    if (this.onerror) {
      const event = new Event('error') as Event & { error?: Error };
      if (error) {
        (event as unknown as { error: Error }).error = error;
      }
      this.onerror(event);
    }
  }

  simulateClose(code: number = 1000, reason: string = ''): void {
    this.readyState = MockWebSocket.CLOSED;
    this.closeReason = { code, reason };

    if (this.onclose) {
      this.onclose(
        new CloseEvent('close', {
          code,
          reason,
          wasClean: code === 1000,
        })
      );
    }
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView): void {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }

    this.messageQueue.push({
      type: 'sent',
      payload: data,
    });
  }

  close(code?: number, reason?: string): void {
    this.readyState = MockWebSocket.CLOSING;

    setTimeout(() => {
      this.simulateClose(code || 1000, reason || '');
    }, 0);
  }

  // Test utilities
  getSentMessages(): unknown[] {
    return this.messageQueue.map((m) => m.payload);
  }

  getLastSentMessage(): unknown {
    return this.messageQueue[this.messageQueue.length - 1]?.payload;
  }

  clearSentMessages(): void {
    this.messageQueue = [];
  }

  getCloseReason(): { code: number; reason: string } | null {
    return this.closeReason;
  }

  addEventListener = vi.fn();
  removeEventListener = vi.fn();
  dispatchEvent = vi.fn(() => true);
}

// =============================================================================
// Mock Socket.IO Client
// =============================================================================

export class MockSocketIO {
  connected: boolean = false;
  id: string = 'mock-socket-id';

  private eventHandlers: Map<string, Set<(...args: unknown[]) => void>> = new Map();
  private autoConnect: boolean;

  constructor(_url?: string, _options?: { autoConnect?: boolean }) {
    this.autoConnect = _options?.autoConnect ?? true;

    if (this.autoConnect) {
      setTimeout(() => this.simulateConnect(), 0);
    }
  }

  connect(): void {
    setTimeout(() => this.simulateConnect(), 0);
  }

  disconnect(): void {
    this.connected = false;
    this.emit('disconnect', 'io client disconnect');
  }

  on(event: string, handler: (...args: unknown[]) => void): this {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);
    return this;
  }

  off(event: string, handler?: (...args: unknown[]) => void): this {
    if (handler) {
      this.eventHandlers.get(event)?.delete(handler);
    } else {
      this.eventHandlers.delete(event);
    }
    return this;
  }

  emit(event: string, ...args: unknown[]): void {
    this.eventHandlers.get(event)?.forEach((handler) => {
      handler(...args);
    });
  }

  simulateConnect(): void {
    this.connected = true;
    this.emit('connect');
  }

  simulateDisconnect(reason: string = 'transport close'): void {
    this.connected = false;
    this.emit('disconnect', reason);
  }

  simulateEvent(event: string, ...args: unknown[]): void {
    this.emit(event, ...args);
  }

  simulateError(error: Error): void {
    this.emit('error', error);
    this.emit('connect_error', error);
  }

  once(event: string, handler: (...args: unknown[]) => void): this {
    const wrappedHandler = (...args: unknown[]) => {
      handler(...args);
      this.off(event, wrappedHandler);
    };
    return this.on(event, wrappedHandler);
  }

  removeAllListeners(event?: string): this {
    if (event) {
      this.eventHandlers.delete(event);
    } else {
      this.eventHandlers.clear();
    }
    return this;
  }
}

// =============================================================================
// Factory Functions
// =============================================================================

export function createMockWebSocket(url: string): MockWebSocket {
  return new MockWebSocket(url);
}

export function createMockSocketIO(url?: string, options?: { autoConnect?: boolean }): MockSocketIO {
  return new MockSocketIO(url, options);
}

// =============================================================================
// Setup Functions
// =============================================================================

let originalWebSocket: typeof WebSocket | undefined;

export function setupMockWebSocket(): void {
  originalWebSocket = global.WebSocket;
  (global as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
}

export function restoreWebSocket(): void {
  if (originalWebSocket) {
    (global as unknown as { WebSocket: typeof WebSocket }).WebSocket = originalWebSocket;
  }
}

// =============================================================================
// Test Helpers
// =============================================================================

export function waitForConnection(socket: MockWebSocket | MockSocketIO, timeout: number = 1000): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Connection timeout'));
    }, timeout);

    if (socket instanceof MockWebSocket) {
      if (socket.readyState === MockWebSocket.OPEN) {
        clearTimeout(timer);
        resolve();
        return;
      }
      socket.onopen = () => {
        clearTimeout(timer);
        resolve();
      };
    } else {
      if (socket.connected) {
        clearTimeout(timer);
        resolve();
        return;
      }
      socket.on('connect', () => {
        clearTimeout(timer);
        resolve();
      });
    }
  });
}

export function waitForMessage<T>(
  socket: MockWebSocket,
  timeout: number = 1000
): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Message timeout'));
    }, timeout);

    socket.onmessage = (ev) => {
      clearTimeout(timer);
      try {
        resolve(JSON.parse(ev.data) as T);
      } catch {
        resolve(ev.data as T);
      }
    };
  });
}

export default {
  MockWebSocket,
  MockSocketIO,
  createMockWebSocket,
  createMockSocketIO,
  setupMockWebSocket,
  restoreWebSocket,
  waitForConnection,
  waitForMessage,
};
