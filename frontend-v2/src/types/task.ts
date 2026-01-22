/**
 * Task Type Definitions
 *
 * Types matching the backend Task model and API schemas.
 */

// Task status values from backend constraint
export type TaskStatus =
  | 'pending'
  | 'queued'
  | 'assigned'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

// Available AI tools
export type ToolType =
  | 'claude_code'
  | 'gemini_cli'
  | 'ollama'
  | 'auto';

// Priority levels (1-10, higher = more urgent)
export type TaskPriority = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;

/**
 * Task interface matching backend TaskResponse schema
 */
export interface Task {
  task_id: string;
  user_id: string | null;
  worker_id: string | null;
  workflow_id: string | null;
  description: string;
  status: TaskStatus;
  progress: number;
  priority: number;
  tool_preference: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

/**
 * Task creation request matching backend TaskCreate schema
 */
export interface TaskCreate {
  description: string;
  tool_preference?: string | null;
  priority?: number;
  workflow_id?: string | null;
  metadata?: Record<string, unknown> | null;
}

/**
 * Task update request matching backend TaskUpdate schema
 */
export interface TaskUpdate {
  description?: string;
  status?: TaskStatus;
  progress?: number;
  priority?: number;
  result?: Record<string, unknown>;
  error?: string;
}

/**
 * Paginated task list response
 */
export interface TaskListResponse {
  tasks: Task[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Task list query parameters
 */
export interface TaskListParams {
  status?: TaskStatus;
  limit?: number;
  offset?: number;
  search?: string;
  sort_by?: 'created_at' | 'updated_at' | 'priority' | 'status';
  sort_order?: 'asc' | 'desc';
}

/**
 * Task log entry
 */
export interface TaskLog {
  id: string;
  task_id: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

/**
 * Task timeline event
 */
export interface TaskTimelineEvent {
  status: TaskStatus;
  timestamp: string;
  description?: string;
}

/**
 * Worker summary for task assignment
 */
export interface WorkerSummary {
  worker_id: string;
  name: string;
  status: 'online' | 'offline' | 'busy';
  supported_tools: string[];
}

/**
 * Status filter tab configuration
 */
export interface StatusTab {
  key: TaskStatus | 'all';
  label: string;
  count?: number;
}

/**
 * Table column sort configuration
 */
export interface SortConfig {
  column: string;
  direction: 'asc' | 'desc';
}

/**
 * Task form data for create/edit
 */
export interface TaskFormData {
  name: string;
  description: string;
  tool_preference: string;
  worker_id: string | null;
  priority: number;
  input_parameters: string; // JSON string
}

/**
 * Helper function to get status display properties
 */
export function getStatusConfig(status: TaskStatus): {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  pulseAnimation: boolean;
} {
  const configs: Record<TaskStatus, ReturnType<typeof getStatusConfig>> = {
    pending: {
      label: 'Pending',
      color: 'text-yellow-700',
      bgColor: 'bg-yellow-100',
      borderColor: 'border-yellow-300',
      pulseAnimation: false,
    },
    queued: {
      label: 'Queued',
      color: 'text-orange-700',
      bgColor: 'bg-orange-100',
      borderColor: 'border-orange-300',
      pulseAnimation: false,
    },
    assigned: {
      label: 'Assigned',
      color: 'text-purple-700',
      bgColor: 'bg-purple-100',
      borderColor: 'border-purple-300',
      pulseAnimation: false,
    },
    running: {
      label: 'Running',
      color: 'text-blue-700',
      bgColor: 'bg-blue-100',
      borderColor: 'border-blue-300',
      pulseAnimation: true,
    },
    completed: {
      label: 'Completed',
      color: 'text-green-700',
      bgColor: 'bg-green-100',
      borderColor: 'border-green-300',
      pulseAnimation: false,
    },
    failed: {
      label: 'Failed',
      color: 'text-red-700',
      bgColor: 'bg-red-100',
      borderColor: 'border-red-300',
      pulseAnimation: false,
    },
    cancelled: {
      label: 'Cancelled',
      color: 'text-gray-700',
      bgColor: 'bg-gray-100',
      borderColor: 'border-gray-300',
      pulseAnimation: false,
    },
  };

  return configs[status];
}

/**
 * Calculate task duration from timestamps
 */
export function calculateDuration(
  startedAt: string | null,
  completedAt: string | null
): string | null {
  if (!startedAt) return null;

  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const durationMs = end - start;

  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }

  const seconds = Math.floor(durationMs / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Format timestamp to human-readable string
 */
export function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString();
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(timestamp: string): string {
  const now = Date.now();
  const time = new Date(timestamp).getTime();
  const diffMs = now - time;

  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) {
    return 'just now';
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);
  if (days < 7) {
    return `${days}d ago`;
  }

  return new Date(timestamp).toLocaleDateString();
}
