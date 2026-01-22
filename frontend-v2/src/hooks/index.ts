// Auth hooks
export { useAuth, useRequireAuth, apiClient } from './useAuth';

// Workers hooks
export {
  useWorkers,
  useWorker,
  useCreateWorker,
  useUpdateWorker,
  useDeleteWorker,
  workerKeys,
} from './useWorkers';

// Tasks hooks
export {
  useTasks,
  useTask,
  useCreateTask,
  useUpdateTask,
  useCancelTask,
  useRetryTask,
  useDeleteTask,
  taskKeys,
} from './useTasks';

// WebSocket hooks
export {
  useWebSocket,
  useWebSocketEvent,
  useWebSocketChannels,
} from './useWebSocket';

// Real-time update hooks
export {
  useTaskUpdates,
  useTaskUpdate,
  useTaskProgress,
  TASK_QUERY_KEYS,
} from './useTaskUpdates';

export {
  useWorkerUpdates,
  useWorkerUpdate,
  useWorkerMetricsHistory,
  useOnlineWorkersCount,
  WORKER_QUERY_KEYS,
} from './useWorkerUpdates';

export {
  useWorkflowUpdates,
  useWorkflowUpdate,
  usePendingReviews,
  useWorkflowsNeedingAttention,
  WORKFLOW_QUERY_KEYS,
} from './useWorkflowUpdates';

// Notification hooks
export {
  useNotifications,
  useUnreadCount,
  useHasUnreadNotifications,
  useNotificationCenterState,
  useToastNotifications,
  useNotificationActions,
} from './useNotifications';
