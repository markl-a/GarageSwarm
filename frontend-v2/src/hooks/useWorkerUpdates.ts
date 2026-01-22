/**
 * useWorkerUpdates Hook
 *
 * Hook for subscribing to real-time worker updates via WebSocket.
 * Tracks worker status changes, metrics, and new worker registrations.
 */

import { useEffect, useCallback, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import websocketService from '../services/websocket';
import { useWebSocketChannels } from './useWebSocket';
import { useNotificationStore } from '../stores/notificationStore';
import {
  WS_EVENTS,
  WorkerStatus,
  WorkerRegisteredPayload,
  WorkerUpdatedPayload,
  WorkerDeletedPayload,
  WorkerStatusChangedPayload,
  WorkerMetricsPayload,
  WorkerHeartbeatPayload,
  WorkerBase,
  WorkerMetrics,
  NotificationType,
  NotificationCategory,
  ConnectionState,
} from '../types/websocket';

// ============================================================================
// Types
// ============================================================================

export interface WorkerUpdateCallbacks {
  onWorkerRegistered?: (payload: WorkerRegisteredPayload) => void;
  onWorkerUpdated?: (payload: WorkerUpdatedPayload) => void;
  onWorkerDeleted?: (payload: WorkerDeletedPayload) => void;
  onWorkerStatusChanged?: (payload: WorkerStatusChangedPayload) => void;
  onWorkerMetrics?: (payload: WorkerMetricsPayload) => void;
  onWorkerHeartbeat?: (payload: WorkerHeartbeatPayload) => void;
}

export interface UseWorkerUpdatesOptions {
  /** Subscribe to specific worker ID */
  workerId?: string;
  /** Enable notifications for worker events */
  enableNotifications?: boolean;
  /** Enable React Query cache updates */
  enableCacheUpdates?: boolean;
  /** Track worker metrics history */
  trackMetricsHistory?: boolean;
  /** Maximum metrics history length */
  maxMetricsHistory?: number;
  /** Custom callbacks for worker events */
  callbacks?: WorkerUpdateCallbacks;
  /** Enable the hook */
  enabled?: boolean;
}

export interface WorkerMetricsHistory {
  workerId: string;
  history: Array<{
    timestamp: string;
    metrics: WorkerMetrics;
  }>;
}

export interface UseWorkerUpdatesReturn {
  /** Map of current worker metrics by worker ID */
  workerMetrics: Map<string, WorkerMetrics>;
  /** Map of worker metrics history by worker ID */
  metricsHistory: Map<string, WorkerMetricsHistory>;
  /** Map of worker online status by worker ID */
  workerOnlineStatus: Map<string, boolean>;
  /** Subscribe to a specific worker's updates */
  subscribeToWorker: (workerId: string) => () => void;
  /** Unsubscribe from a specific worker's updates */
  unsubscribeFromWorker: (workerId: string) => void;
  /** Get metrics for a specific worker */
  getWorkerMetrics: (workerId: string) => WorkerMetrics | undefined;
  /** Check if a worker is online */
  isWorkerOnline: (workerId: string) => boolean;
}

// ============================================================================
// Query Keys
// ============================================================================

export const WORKER_QUERY_KEYS = {
  all: ['workers'] as const,
  lists: () => [...WORKER_QUERY_KEYS.all, 'list'] as const,
  list: (filters: Record<string, unknown>) =>
    [...WORKER_QUERY_KEYS.lists(), filters] as const,
  details: () => [...WORKER_QUERY_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...WORKER_QUERY_KEYS.details(), id] as const,
  metrics: (id: string) => [...WORKER_QUERY_KEYS.detail(id), 'metrics'] as const,
};

// ============================================================================
// Hook Implementation
// ============================================================================

export function useWorkerUpdates(
  options: UseWorkerUpdatesOptions = {}
): UseWorkerUpdatesReturn {
  const {
    workerId,
    enableNotifications = true,
    enableCacheUpdates = true,
    trackMetricsHistory = false,
    maxMetricsHistory = 100,
    callbacks = {},
    enabled = true,
  } = options;

  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((state) => state.addNotification);

  // State for metrics and status tracking
  const [workerMetrics, setWorkerMetrics] = useState<Map<string, WorkerMetrics>>(
    new Map()
  );
  const [metricsHistory, setMetricsHistory] = useState<
    Map<string, WorkerMetricsHistory>
  >(new Map());
  const [workerOnlineStatus, setWorkerOnlineStatus] = useState<
    Map<string, boolean>
  >(new Map());

  // Refs for avoiding stale closures
  const workerMetricsRef = useRef(workerMetrics);
  const metricsHistoryRef = useRef(metricsHistory);
  const workerOnlineStatusRef = useRef(workerOnlineStatus);

  // Keep refs in sync
  useEffect(() => {
    workerMetricsRef.current = workerMetrics;
  }, [workerMetrics]);

  useEffect(() => {
    metricsHistoryRef.current = metricsHistory;
  }, [metricsHistory]);

  useEffect(() => {
    workerOnlineStatusRef.current = workerOnlineStatus;
  }, [workerOnlineStatus]);

  // Subscribe to the workers channel
  useWebSocketChannels(
    workerId ? `worker:${workerId}` : 'workers',
    enabled
  );

  // ============================================================================
  // Cache Update Helpers
  // ============================================================================

  const updateWorkerInCache = useCallback(
    (worker: Partial<WorkerBase> & { id: string }) => {
      if (!enableCacheUpdates) return;

      // Update worker detail cache
      queryClient.setQueryData<WorkerBase>(
        WORKER_QUERY_KEYS.detail(worker.id),
        (oldData) => (oldData ? { ...oldData, ...worker } : undefined)
      );

      // Update worker lists cache
      queryClient.setQueriesData<{ workers: WorkerBase[] }>(
        { queryKey: WORKER_QUERY_KEYS.lists() },
        (oldData) => {
          if (!oldData?.workers) return oldData;
          return {
            ...oldData,
            workers: oldData.workers.map((w) =>
              w.id === worker.id ? { ...w, ...worker } : w
            ),
          };
        }
      );
    },
    [queryClient, enableCacheUpdates]
  );

  const addWorkerToCache = useCallback(
    (worker: WorkerBase) => {
      if (!enableCacheUpdates) return;

      // Set worker detail
      queryClient.setQueryData(WORKER_QUERY_KEYS.detail(worker.id), worker);

      // Invalidate lists to refetch
      queryClient.invalidateQueries({ queryKey: WORKER_QUERY_KEYS.lists() });
    },
    [queryClient, enableCacheUpdates]
  );

  const removeWorkerFromCache = useCallback(
    (workerIdToRemove: string) => {
      if (!enableCacheUpdates) return;

      // Remove worker detail
      queryClient.removeQueries({
        queryKey: WORKER_QUERY_KEYS.detail(workerIdToRemove),
      });

      // Update lists cache
      queryClient.setQueriesData<{ workers: WorkerBase[] }>(
        { queryKey: WORKER_QUERY_KEYS.lists() },
        (oldData) => {
          if (!oldData?.workers) return oldData;
          return {
            ...oldData,
            workers: oldData.workers.filter((w) => w.id !== workerIdToRemove),
          };
        }
      );
    },
    [queryClient, enableCacheUpdates]
  );

  // ============================================================================
  // Metrics Helpers
  // ============================================================================

  const updateWorkerMetrics = useCallback(
    (id: string, metrics: WorkerMetrics, timestamp: string) => {
      setWorkerMetrics((prev) => {
        const next = new Map(prev);
        next.set(id, metrics);
        return next;
      });

      if (trackMetricsHistory) {
        setMetricsHistory((prev) => {
          const next = new Map(prev);
          const existing = next.get(id) || { workerId: id, history: [] };

          const newHistory = [
            ...existing.history,
            { timestamp, metrics },
          ].slice(-maxMetricsHistory);

          next.set(id, { workerId: id, history: newHistory });
          return next;
        });
      }
    },
    [trackMetricsHistory, maxMetricsHistory]
  );

  const updateWorkerOnlineStatus = useCallback((id: string, isOnline: boolean) => {
    setWorkerOnlineStatus((prev) => {
      const next = new Map(prev);
      next.set(id, isOnline);
      return next;
    });
  }, []);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  useEffect(() => {
    if (!enabled) return;

    const unsubscribers: (() => void)[] = [];

    // Worker Registered
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKER_REGISTERED,
        (payload: WorkerRegisteredPayload) => {
          addWorkerToCache(payload.worker);
          updateWorkerOnlineStatus(payload.worker.id, true);

          if (enableNotifications) {
            addNotification({
              type: NotificationType.SUCCESS,
              category: NotificationCategory.WORKER,
              title: 'New Worker Registered',
              message: `Worker "${payload.worker.name}" (${payload.worker.type}) has connected`,
              link: `/workers/${payload.worker.id}`,
            });
          }

          callbacks.onWorkerRegistered?.(payload);
        }
      )
    );

    // Worker Updated
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKER_UPDATED,
        (payload: WorkerUpdatedPayload) => {
          updateWorkerInCache(payload.worker);
          callbacks.onWorkerUpdated?.(payload);
        }
      )
    );

    // Worker Deleted
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKER_DELETED,
        (payload: WorkerDeletedPayload) => {
          removeWorkerFromCache(payload.workerId);

          // Clean up local state
          setWorkerMetrics((prev) => {
            const next = new Map(prev);
            next.delete(payload.workerId);
            return next;
          });

          setMetricsHistory((prev) => {
            const next = new Map(prev);
            next.delete(payload.workerId);
            return next;
          });

          setWorkerOnlineStatus((prev) => {
            const next = new Map(prev);
            next.delete(payload.workerId);
            return next;
          });

          callbacks.onWorkerDeleted?.(payload);
        }
      )
    );

    // Worker Status Changed
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKER_STATUS_CHANGED,
        (payload: WorkerStatusChangedPayload) => {
          updateWorkerInCache({
            id: payload.workerId,
            status: payload.newStatus,
            updatedAt: payload.timestamp,
          });

          const isOnline =
            payload.newStatus !== WorkerStatus.OFFLINE &&
            payload.newStatus !== WorkerStatus.ERROR;
          updateWorkerOnlineStatus(payload.workerId, isOnline);

          if (enableNotifications) {
            if (payload.newStatus === WorkerStatus.OFFLINE) {
              addNotification({
                type: NotificationType.WARNING,
                category: NotificationCategory.WORKER,
                title: 'Worker Offline',
                message: payload.reason || 'Worker has disconnected',
                link: `/workers/${payload.workerId}`,
              });
            } else if (payload.newStatus === WorkerStatus.ERROR) {
              addNotification({
                type: NotificationType.ERROR,
                category: NotificationCategory.WORKER,
                title: 'Worker Error',
                message: payload.reason || 'Worker encountered an error',
                link: `/workers/${payload.workerId}`,
              });
            }
          }

          callbacks.onWorkerStatusChanged?.(payload);
        }
      )
    );

    // Worker Metrics
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKER_METRICS,
        (payload: WorkerMetricsPayload) => {
          updateWorkerMetrics(
            payload.workerId,
            payload.metrics,
            payload.timestamp
          );
          callbacks.onWorkerMetrics?.(payload);
        }
      )
    );

    // Worker Heartbeat
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKER_HEARTBEAT,
        (payload: WorkerHeartbeatPayload) => {
          updateWorkerInCache({
            id: payload.workerId,
            status: payload.status,
            currentTaskId: payload.currentTaskId,
            lastHeartbeat: payload.timestamp,
          });

          updateWorkerOnlineStatus(payload.workerId, true);

          callbacks.onWorkerHeartbeat?.(payload);
        }
      )
    );

    return () => {
      unsubscribers.forEach((unsubscribe) => unsubscribe());
    };
  }, [
    enabled,
    enableNotifications,
    enableCacheUpdates,
    addWorkerToCache,
    updateWorkerInCache,
    removeWorkerFromCache,
    updateWorkerMetrics,
    updateWorkerOnlineStatus,
    addNotification,
    callbacks,
  ]);

  // ============================================================================
  // Worker Subscription Management
  // ============================================================================

  const subscribeToWorker = useCallback((id: string): (() => void) => {
    const channel = `worker:${id}` as const;

    if (websocketService.isConnected()) {
      websocketService.subscribe(channel);
    }

    const unsubscribeState = websocketService.onStateChange((state) => {
      if (state === ConnectionState.CONNECTED) {
        websocketService.subscribe(channel);
      }
    });

    return () => {
      unsubscribeState();
      if (websocketService.isConnected()) {
        websocketService.unsubscribe(channel);
      }
    };
  }, []);

  const unsubscribeFromWorker = useCallback((id: string): void => {
    if (websocketService.isConnected()) {
      websocketService.unsubscribe(`worker:${id}`);
    }
  }, []);

  // ============================================================================
  // Utility Functions
  // ============================================================================

  const getWorkerMetrics = useCallback(
    (id: string): WorkerMetrics | undefined => {
      return workerMetrics.get(id);
    },
    [workerMetrics]
  );

  const isWorkerOnline = useCallback(
    (id: string): boolean => {
      return workerOnlineStatus.get(id) ?? false;
    },
    [workerOnlineStatus]
  );

  return {
    workerMetrics,
    metricsHistory,
    workerOnlineStatus,
    subscribeToWorker,
    unsubscribeFromWorker,
    getWorkerMetrics,
    isWorkerOnline,
  };
}

// ============================================================================
// Specialized Hooks
// ============================================================================

/**
 * Hook to subscribe to a single worker's updates
 */
export function useWorkerUpdate(
  workerId: string | undefined,
  callbacks?: WorkerUpdateCallbacks
): {
  metrics: WorkerMetrics | undefined;
  isOnline: boolean;
} {
  const { workerMetrics, workerOnlineStatus } = useWorkerUpdates({
    workerId,
    callbacks,
    enabled: !!workerId,
  });

  return {
    metrics: workerId ? workerMetrics.get(workerId) : undefined,
    isOnline: workerId ? (workerOnlineStatus.get(workerId) ?? false) : false,
  };
}

/**
 * Hook to track worker metrics with history
 */
export function useWorkerMetricsHistory(
  workerId: string,
  maxHistory = 100
): WorkerMetricsHistory | undefined {
  const { metricsHistory } = useWorkerUpdates({
    workerId,
    trackMetricsHistory: true,
    maxMetricsHistory: maxHistory,
    enableNotifications: false,
  });

  return metricsHistory.get(workerId);
}

/**
 * Hook to get online workers count
 */
export function useOnlineWorkersCount(): number {
  const { workerOnlineStatus } = useWorkerUpdates({
    enableNotifications: false,
  });

  return Array.from(workerOnlineStatus.values()).filter(Boolean).length;
}

export default useWorkerUpdates;
