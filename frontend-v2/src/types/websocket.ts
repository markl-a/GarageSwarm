/**
 * WebSocket Message Types for GarageSwarm
 *
 * Defines all message types exchanged between frontend and backend
 * via Socket.IO for real-time updates.
 */

// ============================================================================
// Enums
// ============================================================================

export enum ConnectionState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
}

export enum TaskStatus {
  PENDING = 'pending',
  ASSIGNED = 'assigned',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum WorkerStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  BUSY = 'busy',
  IDLE = 'idle',
  ERROR = 'error',
}

export enum WorkflowStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  PAUSED = 'paused',
  WAITING_REVIEW = 'waiting_review',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum NodeStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped',
  WAITING_REVIEW = 'waiting_review',
}

export enum NotificationType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error',
}

export enum NotificationCategory {
  TASK = 'task',
  WORKER = 'worker',
  WORKFLOW = 'workflow',
  SYSTEM = 'system',
}

// ============================================================================
// WebSocket Event Names
// ============================================================================

export const WS_EVENTS = {
  // Connection events
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  CONNECT_ERROR: 'connect_error',
  RECONNECT: 'reconnect',
  RECONNECT_ATTEMPT: 'reconnect_attempt',
  RECONNECT_ERROR: 'reconnect_error',
  RECONNECT_FAILED: 'reconnect_failed',

  // Heartbeat
  PING: 'ping',
  PONG: 'pong',

  // Task events
  TASK_CREATED: 'task:created',
  TASK_UPDATED: 'task:updated',
  TASK_DELETED: 'task:deleted',
  TASK_STATUS_CHANGED: 'task:status_changed',
  TASK_PROGRESS: 'task:progress',
  TASK_COMPLETED: 'task:completed',
  TASK_FAILED: 'task:failed',

  // Worker events
  WORKER_REGISTERED: 'worker:registered',
  WORKER_UPDATED: 'worker:updated',
  WORKER_DELETED: 'worker:deleted',
  WORKER_STATUS_CHANGED: 'worker:status_changed',
  WORKER_METRICS: 'worker:metrics',
  WORKER_HEARTBEAT: 'worker:heartbeat',

  // Workflow events
  WORKFLOW_CREATED: 'workflow:created',
  WORKFLOW_UPDATED: 'workflow:updated',
  WORKFLOW_DELETED: 'workflow:deleted',
  WORKFLOW_STATUS_CHANGED: 'workflow:status_changed',
  WORKFLOW_NODE_UPDATED: 'workflow:node_updated',
  WORKFLOW_REVIEW_REQUESTED: 'workflow:review_requested',
  WORKFLOW_COMPLETED: 'workflow:completed',
  WORKFLOW_FAILED: 'workflow:failed',

  // Notification events
  NOTIFICATION: 'notification',
  NOTIFICATION_READ: 'notification:read',
  NOTIFICATION_CLEAR: 'notification:clear',

  // Subscription management
  SUBSCRIBE: 'subscribe',
  UNSUBSCRIBE: 'unsubscribe',
} as const;

export type WSEventName = typeof WS_EVENTS[keyof typeof WS_EVENTS];

// ============================================================================
// Base Message Types
// ============================================================================

export interface WSMessage<T = unknown> {
  event: string;
  data: T;
  timestamp: string;
  correlationId?: string;
}

export interface WSError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// Task Message Types
// ============================================================================

export interface TaskBase {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: number;
  tool: string;
  workerId?: string;
  workflowId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface TaskCreatedPayload {
  task: TaskBase;
}

export interface TaskUpdatedPayload {
  task: TaskBase;
  changes: Partial<TaskBase>;
}

export interface TaskDeletedPayload {
  taskId: string;
}

export interface TaskStatusChangedPayload {
  taskId: string;
  previousStatus: TaskStatus;
  newStatus: TaskStatus;
  workerId?: string;
  timestamp: string;
}

export interface TaskProgressPayload {
  taskId: string;
  progress: number; // 0-100
  message?: string;
  details?: Record<string, unknown>;
}

export interface TaskCompletedPayload {
  taskId: string;
  result?: Record<string, unknown>;
  duration: number; // milliseconds
  workerId: string;
}

export interface TaskFailedPayload {
  taskId: string;
  error: WSError;
  workerId?: string;
  retryable: boolean;
}

// ============================================================================
// Worker Message Types
// ============================================================================

export interface WorkerBase {
  id: string;
  name: string;
  type: 'desktop' | 'docker' | 'mobile';
  status: WorkerStatus;
  capabilities: string[];
  currentTaskId?: string;
  lastHeartbeat: string;
  createdAt: string;
  updatedAt: string;
}

export interface WorkerMetrics {
  cpuUsage: number; // 0-100
  memoryUsage: number; // 0-100
  diskUsage?: number; // 0-100
  taskCount: number;
  tasksCompleted: number;
  tasksFailed: number;
  uptime: number; // seconds
}

export interface WorkerRegisteredPayload {
  worker: WorkerBase;
}

export interface WorkerUpdatedPayload {
  worker: WorkerBase;
  changes: Partial<WorkerBase>;
}

export interface WorkerDeletedPayload {
  workerId: string;
}

export interface WorkerStatusChangedPayload {
  workerId: string;
  previousStatus: WorkerStatus;
  newStatus: WorkerStatus;
  reason?: string;
  timestamp: string;
}

export interface WorkerMetricsPayload {
  workerId: string;
  metrics: WorkerMetrics;
  timestamp: string;
}

export interface WorkerHeartbeatPayload {
  workerId: string;
  status: WorkerStatus;
  currentTaskId?: string;
  timestamp: string;
}

// ============================================================================
// Workflow Message Types
// ============================================================================

export interface WorkflowNode {
  id: string;
  type: string;
  status: NodeStatus;
  taskId?: string;
  data: Record<string, unknown>;
  position: { x: number; y: number };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  label?: string;
}

export interface WorkflowBase {
  id: string;
  name: string;
  description?: string;
  status: WorkflowStatus;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  currentNodeId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowCreatedPayload {
  workflow: WorkflowBase;
}

export interface WorkflowUpdatedPayload {
  workflow: WorkflowBase;
  changes: Partial<WorkflowBase>;
}

export interface WorkflowDeletedPayload {
  workflowId: string;
}

export interface WorkflowStatusChangedPayload {
  workflowId: string;
  previousStatus: WorkflowStatus;
  newStatus: WorkflowStatus;
  timestamp: string;
}

export interface WorkflowNodeUpdatedPayload {
  workflowId: string;
  node: WorkflowNode;
  previousStatus?: NodeStatus;
}

export interface HumanReviewRequest {
  id: string;
  workflowId: string;
  nodeId: string;
  title: string;
  description: string;
  options: {
    label: string;
    value: string;
    description?: string;
  }[];
  data?: Record<string, unknown>;
  createdAt: string;
  expiresAt?: string;
}

export interface WorkflowReviewRequestedPayload {
  workflowId: string;
  nodeId: string;
  review: HumanReviewRequest;
}

export interface WorkflowCompletedPayload {
  workflowId: string;
  result?: Record<string, unknown>;
  duration: number;
  stats: {
    nodesExecuted: number;
    nodesFailed: number;
    nodesSkipped: number;
  };
}

export interface WorkflowFailedPayload {
  workflowId: string;
  nodeId: string;
  error: WSError;
  recoverable: boolean;
}

// ============================================================================
// Notification Message Types
// ============================================================================

export interface Notification {
  id: string;
  type: NotificationType;
  category: NotificationCategory;
  title: string;
  message: string;
  data?: Record<string, unknown>;
  link?: string;
  read: boolean;
  createdAt: string;
}

export interface NotificationPayload {
  notification: Notification;
}

export interface NotificationReadPayload {
  notificationId: string;
}

export interface NotificationClearPayload {
  notificationIds?: string[]; // If empty, clear all
}

// ============================================================================
// Subscription Types
// ============================================================================

export type SubscriptionChannel =
  | 'tasks'
  | 'workers'
  | 'workflows'
  | 'notifications'
  | `task:${string}`      // Subscribe to specific task
  | `worker:${string}`    // Subscribe to specific worker
  | `workflow:${string}`; // Subscribe to specific workflow

export interface SubscribePayload {
  channels: SubscriptionChannel[];
}

export interface UnsubscribePayload {
  channels: SubscriptionChannel[];
}

// ============================================================================
// Event Callback Types
// ============================================================================

export type TaskEventCallback =
  | { event: typeof WS_EVENTS.TASK_CREATED; callback: (payload: TaskCreatedPayload) => void }
  | { event: typeof WS_EVENTS.TASK_UPDATED; callback: (payload: TaskUpdatedPayload) => void }
  | { event: typeof WS_EVENTS.TASK_DELETED; callback: (payload: TaskDeletedPayload) => void }
  | { event: typeof WS_EVENTS.TASK_STATUS_CHANGED; callback: (payload: TaskStatusChangedPayload) => void }
  | { event: typeof WS_EVENTS.TASK_PROGRESS; callback: (payload: TaskProgressPayload) => void }
  | { event: typeof WS_EVENTS.TASK_COMPLETED; callback: (payload: TaskCompletedPayload) => void }
  | { event: typeof WS_EVENTS.TASK_FAILED; callback: (payload: TaskFailedPayload) => void };

export type WorkerEventCallback =
  | { event: typeof WS_EVENTS.WORKER_REGISTERED; callback: (payload: WorkerRegisteredPayload) => void }
  | { event: typeof WS_EVENTS.WORKER_UPDATED; callback: (payload: WorkerUpdatedPayload) => void }
  | { event: typeof WS_EVENTS.WORKER_DELETED; callback: (payload: WorkerDeletedPayload) => void }
  | { event: typeof WS_EVENTS.WORKER_STATUS_CHANGED; callback: (payload: WorkerStatusChangedPayload) => void }
  | { event: typeof WS_EVENTS.WORKER_METRICS; callback: (payload: WorkerMetricsPayload) => void }
  | { event: typeof WS_EVENTS.WORKER_HEARTBEAT; callback: (payload: WorkerHeartbeatPayload) => void };

export type WorkflowEventCallback =
  | { event: typeof WS_EVENTS.WORKFLOW_CREATED; callback: (payload: WorkflowCreatedPayload) => void }
  | { event: typeof WS_EVENTS.WORKFLOW_UPDATED; callback: (payload: WorkflowUpdatedPayload) => void }
  | { event: typeof WS_EVENTS.WORKFLOW_DELETED; callback: (payload: WorkflowDeletedPayload) => void }
  | { event: typeof WS_EVENTS.WORKFLOW_STATUS_CHANGED; callback: (payload: WorkflowStatusChangedPayload) => void }
  | { event: typeof WS_EVENTS.WORKFLOW_NODE_UPDATED; callback: (payload: WorkflowNodeUpdatedPayload) => void }
  | { event: typeof WS_EVENTS.WORKFLOW_REVIEW_REQUESTED; callback: (payload: WorkflowReviewRequestedPayload) => void }
  | { event: typeof WS_EVENTS.WORKFLOW_COMPLETED; callback: (payload: WorkflowCompletedPayload) => void }
  | { event: typeof WS_EVENTS.WORKFLOW_FAILED; callback: (payload: WorkflowFailedPayload) => void };

export type NotificationEventCallback =
  | { event: typeof WS_EVENTS.NOTIFICATION; callback: (payload: NotificationPayload) => void };

// Generic event handler type
export type EventHandler<T = unknown> = (payload: T) => void;

// Map of event names to their payload types
export interface WSEventPayloadMap {
  [WS_EVENTS.TASK_CREATED]: TaskCreatedPayload;
  [WS_EVENTS.TASK_UPDATED]: TaskUpdatedPayload;
  [WS_EVENTS.TASK_DELETED]: TaskDeletedPayload;
  [WS_EVENTS.TASK_STATUS_CHANGED]: TaskStatusChangedPayload;
  [WS_EVENTS.TASK_PROGRESS]: TaskProgressPayload;
  [WS_EVENTS.TASK_COMPLETED]: TaskCompletedPayload;
  [WS_EVENTS.TASK_FAILED]: TaskFailedPayload;

  [WS_EVENTS.WORKER_REGISTERED]: WorkerRegisteredPayload;
  [WS_EVENTS.WORKER_UPDATED]: WorkerUpdatedPayload;
  [WS_EVENTS.WORKER_DELETED]: WorkerDeletedPayload;
  [WS_EVENTS.WORKER_STATUS_CHANGED]: WorkerStatusChangedPayload;
  [WS_EVENTS.WORKER_METRICS]: WorkerMetricsPayload;
  [WS_EVENTS.WORKER_HEARTBEAT]: WorkerHeartbeatPayload;

  [WS_EVENTS.WORKFLOW_CREATED]: WorkflowCreatedPayload;
  [WS_EVENTS.WORKFLOW_UPDATED]: WorkflowUpdatedPayload;
  [WS_EVENTS.WORKFLOW_DELETED]: WorkflowDeletedPayload;
  [WS_EVENTS.WORKFLOW_STATUS_CHANGED]: WorkflowStatusChangedPayload;
  [WS_EVENTS.WORKFLOW_NODE_UPDATED]: WorkflowNodeUpdatedPayload;
  [WS_EVENTS.WORKFLOW_REVIEW_REQUESTED]: WorkflowReviewRequestedPayload;
  [WS_EVENTS.WORKFLOW_COMPLETED]: WorkflowCompletedPayload;
  [WS_EVENTS.WORKFLOW_FAILED]: WorkflowFailedPayload;

  [WS_EVENTS.NOTIFICATION]: NotificationPayload;
  [WS_EVENTS.NOTIFICATION_READ]: NotificationReadPayload;
  [WS_EVENTS.NOTIFICATION_CLEAR]: NotificationClearPayload;
}
