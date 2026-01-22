/**
 * Worker Types
 *
 * TypeScript type definitions for worker-related data structures.
 */

// Worker status enum
export type WorkerStatus = 'online' | 'offline' | 'busy' | 'idle';

// Available AI tools
export type ToolName = 'claude_code' | 'gemini_cli' | 'ollama' | string;

// Tool status
export type ToolStatus = 'available' | 'busy' | 'unavailable' | 'error';

// System info structure
export interface SystemInfo {
  os?: string;
  cpu?: string;
  memory_total_gb?: number;
  disk_total_gb?: number;
  platform?: string;
  architecture?: string;
  [key: string]: string | number | undefined;
}

// Worker interface matching backend WorkerResponse
export interface Worker {
  worker_id: string;
  machine_id: string;
  machine_name: string;
  status: WorkerStatus;
  tools: ToolName[];
  system_info?: SystemInfo | null;
  cpu_percent?: number | null;
  memory_percent?: number | null;
  disk_percent?: number | null;
  last_heartbeat?: string | null;
  registered_at: string;
  is_active?: boolean;
}

// Worker registration request
export interface WorkerRegisterRequest {
  machine_id: string;
  machine_name: string;
  tools: ToolName[];
  system_info?: SystemInfo | null;
}

// Worker heartbeat request
export interface WorkerHeartbeatRequest {
  status: WorkerStatus;
  cpu_percent?: number | null;
  memory_percent?: number | null;
  disk_percent?: number | null;
  tools?: ToolName[] | null;
  current_task_id?: string | null;
}

// Worker list response
export interface WorkerListResponse {
  workers: Worker[];
  total: number;
  limit: number;
  offset: number;
}

// Worker filter options
export interface WorkerFilters {
  status?: WorkerStatus | 'all';
  tools?: ToolName[];
  search?: string;
}

// Worker sort options
export type WorkerSortField = 'machine_name' | 'status' | 'last_heartbeat' | 'registered_at';
export type SortDirection = 'asc' | 'desc';

export interface WorkerSortOptions {
  field: WorkerSortField;
  direction: SortDirection;
}

// Worker metrics history point
export interface MetricsDataPoint {
  timestamp: string;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
}

// Worker metrics summary
export interface WorkerMetricsSummary {
  current_cpu: number;
  current_memory: number;
  current_disk: number;
  avg_cpu_24h?: number;
  avg_memory_24h?: number;
  task_completion_rate?: number;
  avg_execution_time_ms?: number;
  total_tasks_completed?: number;
  total_tasks_failed?: number;
}

// Worker task history item
export interface WorkerTaskHistoryItem {
  task_id: string;
  description: string;
  status: string;
  priority: number;
  tool_preference?: string | null;
  created_at: string;
  completed_at?: string | null;
  execution_time_ms?: number | null;
}

// Worker form data for create/edit
export interface WorkerFormData {
  machine_name: string;
  description?: string;
  tools: ToolName[];
  is_active: boolean;
}

// Tool with status info
export interface ToolInfo {
  name: ToolName;
  status: ToolStatus;
  version?: string;
  last_used?: string;
}

// View mode for worker list
export type ViewMode = 'grid' | 'table';

// Bulk action types
export type BulkAction = 'activate' | 'deactivate' | 'delete';
