/**
 * useTaskUpdates Hook
 *
 * Hook for subscribing to real-time task updates via WebSocket.
 * Integrates with React Query for cache updates and provides
 * notification callbacks for task events.
 */

import { useEffect, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import websocketService from '../services/websocket';
import { useWebSocketChannels } from './useWebSocket';
import { useNotificationStore } from '../stores/notificationStore';
import {
  WS_EVENTS,
  TaskStatus,
  TaskCreatedPayload,
  TaskUpdatedPayload,
  TaskDeletedPayload,
  TaskStatusChangedPayload,
  TaskProgressPayload,
  TaskCompletedPayload,
  TaskFailedPayload,
  TaskBase,
  NotificationType,
  NotificationCategory,
  ConnectionState,
} from '../types/websocket';

// ============================================================================
// Types
// ============================================================================

export interface TaskUpdateCallbacks {
  onTaskCreated?: (payload: TaskCreatedPayload) => void;
  onTaskUpdated?: (payload: TaskUpdatedPayload) => void;
  onTaskDeleted?: (payload: TaskDeletedPayload) => void;
  onTaskStatusChanged?: (payload: TaskStatusChangedPayload) => void;
  onTaskProgress?: (payload: TaskProgressPayload) => void;
  onTaskCompleted?: (payload: TaskCompletedPayload) => void;
  onTaskFailed?: (payload: TaskFailedPayload) => void;
}

export interface UseTaskUpdatesOptions {
  /** Subscribe to specific task ID */
  taskId?: string;
  /** Enable notifications for task events */
  enableNotifications?: boolean;
  /** Enable React Query cache updates */
  enableCacheUpdates?: boolean;
  /** Custom callbacks for task events */
  callbacks?: TaskUpdateCallbacks;
  /** Enable the hook */
  enabled?: boolean;
}

export interface TaskProgressState {
  taskId: string;
  progress: number;
  message?: string;
}

export interface UseTaskUpdatesReturn {
  /** Map of task progress by task ID */
  taskProgress: Map<string, TaskProgressState>;
  /** Subscribe to a specific task's updates */
  subscribeToTask: (taskId: string) => () => void;
  /** Unsubscribe from a specific task's updates */
  unsubscribeFromTask: (taskId: string) => void;
}

// ============================================================================
// Query Keys
// ============================================================================

export const TASK_QUERY_KEYS = {
  all: ['tasks'] as const,
  lists: () => [...TASK_QUERY_KEYS.all, 'list'] as const,
  list: (filters: Record<string, unknown>) =>
    [...TASK_QUERY_KEYS.lists(), filters] as const,
  details: () => [...TASK_QUERY_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...TASK_QUERY_KEYS.details(), id] as const,
};

// ============================================================================
// Hook Implementation
// ============================================================================

export function useTaskUpdates(
  options: UseTaskUpdatesOptions = {}
): UseTaskUpdatesReturn {
  const {
    taskId,
    enableNotifications = true,
    enableCacheUpdates = true,
    callbacks = {},
    enabled = true,
  } = options;

  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((state) => state.addNotification);

  // Track task progress
  const taskProgressRef = useRef<Map<string, TaskProgressState>>(new Map());

  // Subscribe to the tasks channel
  useWebSocketChannels(
    taskId ? `task:${taskId}` : 'tasks',
    enabled
  );

  // ============================================================================
  // Cache Update Helpers
  // ============================================================================

  const updateTaskInCache = useCallback(
    (task: Partial<TaskBase> & { id: string }) => {
      if (!enableCacheUpdates) return;

      // Update task detail cache
      queryClient.setQueryData<TaskBase>(
        TASK_QUERY_KEYS.detail(task.id),
        (oldData) => (oldData ? { ...oldData, ...task } : undefined)
      );

      // Update task lists cache
      queryClient.setQueriesData<{ tasks: TaskBase[] }>(
        { queryKey: TASK_QUERY_KEYS.lists() },
        (oldData) => {
          if (!oldData?.tasks) return oldData;
          return {
            ...oldData,
            tasks: oldData.tasks.map((t) =>
              t.id === task.id ? { ...t, ...task } : t
            ),
          };
        }
      );
    },
    [queryClient, enableCacheUpdates]
  );

  const addTaskToCache = useCallback(
    (task: TaskBase) => {
      if (!enableCacheUpdates) return;

      // Set task detail
      queryClient.setQueryData(TASK_QUERY_KEYS.detail(task.id), task);

      // Invalidate lists to refetch
      queryClient.invalidateQueries({ queryKey: TASK_QUERY_KEYS.lists() });
    },
    [queryClient, enableCacheUpdates]
  );

  const removeTaskFromCache = useCallback(
    (taskIdToRemove: string) => {
      if (!enableCacheUpdates) return;

      // Remove task detail
      queryClient.removeQueries({
        queryKey: TASK_QUERY_KEYS.detail(taskIdToRemove),
      });

      // Update lists cache
      queryClient.setQueriesData<{ tasks: TaskBase[] }>(
        { queryKey: TASK_QUERY_KEYS.lists() },
        (oldData) => {
          if (!oldData?.tasks) return oldData;
          return {
            ...oldData,
            tasks: oldData.tasks.filter((t) => t.id !== taskIdToRemove),
          };
        }
      );
    },
    [queryClient, enableCacheUpdates]
  );

  // ============================================================================
  // Event Handlers
  // ============================================================================

  useEffect(() => {
    if (!enabled) return;

    const unsubscribers: (() => void)[] = [];

    // Task Created
    unsubscribers.push(
      websocketService.on(WS_EVENTS.TASK_CREATED, (payload: TaskCreatedPayload) => {
        addTaskToCache(payload.task);

        if (enableNotifications) {
          addNotification({
            type: NotificationType.INFO,
            category: NotificationCategory.TASK,
            title: 'New Task Created',
            message: `Task "${payload.task.title}" has been created`,
            link: `/tasks/${payload.task.id}`,
          });
        }

        callbacks.onTaskCreated?.(payload);
      })
    );

    // Task Updated
    unsubscribers.push(
      websocketService.on(WS_EVENTS.TASK_UPDATED, (payload: TaskUpdatedPayload) => {
        updateTaskInCache(payload.task);
        callbacks.onTaskUpdated?.(payload);
      })
    );

    // Task Deleted
    unsubscribers.push(
      websocketService.on(WS_EVENTS.TASK_DELETED, (payload: TaskDeletedPayload) => {
        removeTaskFromCache(payload.taskId);
        taskProgressRef.current.delete(payload.taskId);
        callbacks.onTaskDeleted?.(payload);
      })
    );

    // Task Status Changed
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.TASK_STATUS_CHANGED,
        (payload: TaskStatusChangedPayload) => {
          updateTaskInCache({
            id: payload.taskId,
            status: payload.newStatus,
            workerId: payload.workerId,
            updatedAt: payload.timestamp,
          });

          if (enableNotifications && payload.newStatus === TaskStatus.RUNNING) {
            addNotification({
              type: NotificationType.INFO,
              category: NotificationCategory.TASK,
              title: 'Task Started',
              message: `Task is now running on worker`,
              link: `/tasks/${payload.taskId}`,
            });
          }

          callbacks.onTaskStatusChanged?.(payload);
        }
      )
    );

    // Task Progress
    unsubscribers.push(
      websocketService.on(WS_EVENTS.TASK_PROGRESS, (payload: TaskProgressPayload) => {
        taskProgressRef.current.set(payload.taskId, {
          taskId: payload.taskId,
          progress: payload.progress,
          message: payload.message,
        });

        callbacks.onTaskProgress?.(payload);
      })
    );

    // Task Completed
    unsubscribers.push(
      websocketService.on(WS_EVENTS.TASK_COMPLETED, (payload: TaskCompletedPayload) => {
        updateTaskInCache({
          id: payload.taskId,
          status: TaskStatus.COMPLETED,
        });

        taskProgressRef.current.delete(payload.taskId);

        if (enableNotifications) {
          const durationSec = Math.round(payload.duration / 1000);
          addNotification({
            type: NotificationType.SUCCESS,
            category: NotificationCategory.TASK,
            title: 'Task Completed',
            message: `Task completed successfully in ${durationSec}s`,
            link: `/tasks/${payload.taskId}`,
          });
        }

        callbacks.onTaskCompleted?.(payload);
      })
    );

    // Task Failed
    unsubscribers.push(
      websocketService.on(WS_EVENTS.TASK_FAILED, (payload: TaskFailedPayload) => {
        updateTaskInCache({
          id: payload.taskId,
          status: TaskStatus.FAILED,
        });

        taskProgressRef.current.delete(payload.taskId);

        if (enableNotifications) {
          addNotification({
            type: NotificationType.ERROR,
            category: NotificationCategory.TASK,
            title: 'Task Failed',
            message: payload.error.message,
            link: `/tasks/${payload.taskId}`,
          });
        }

        callbacks.onTaskFailed?.(payload);
      })
    );

    return () => {
      unsubscribers.forEach((unsubscribe) => unsubscribe());
    };
  }, [
    enabled,
    enableNotifications,
    enableCacheUpdates,
    addTaskToCache,
    updateTaskInCache,
    removeTaskFromCache,
    addNotification,
    callbacks,
  ]);

  // ============================================================================
  // Task Subscription Management
  // ============================================================================

  const subscribeToTask = useCallback((id: string): (() => void) => {
    const channel = `task:${id}` as const;

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

  const unsubscribeFromTask = useCallback((id: string): void => {
    if (websocketService.isConnected()) {
      websocketService.unsubscribe(`task:${id}`);
    }
  }, []);

  return {
    taskProgress: taskProgressRef.current,
    subscribeToTask,
    unsubscribeFromTask,
  };
}

// ============================================================================
// Specialized Hooks
// ============================================================================

/**
 * Hook to subscribe to a single task's updates
 */
export function useTaskUpdate(
  taskId: string | undefined,
  callbacks?: TaskUpdateCallbacks
): {
  progress: TaskProgressState | undefined;
} {
  const { taskProgress } = useTaskUpdates({
    taskId,
    callbacks,
    enabled: !!taskId,
  });

  return {
    progress: taskId ? taskProgress.get(taskId) : undefined,
  };
}

/**
 * Hook to get task progress
 */
export function useTaskProgress(taskId: string): TaskProgressState | null {
  const { taskProgress } = useTaskUpdates({
    taskId,
    enableNotifications: false,
  });

  return taskProgress.get(taskId) || null;
}

export default useTaskUpdates;
