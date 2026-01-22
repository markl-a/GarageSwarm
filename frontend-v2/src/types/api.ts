/**
 * API Types for GarageSwarm Frontend
 *
 * TypeScript type definitions matching the backend API schemas.
 */

// =============================================================================
// Common Types
// =============================================================================

export type UUID = string;

export interface PaginatedResponse<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

// =============================================================================
// Authentication Types
// =============================================================================

export interface UserRegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface UserLoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface UserResponse {
  user_id: UUID;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

// =============================================================================
// Task Types
// =============================================================================

export type TaskStatus =
  | 'pending'
  | 'assigned'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface TaskCreateRequest {
  description: string;
  tool_preference?: string | null;
  priority?: number;
  workflow_id?: UUID | null;
  metadata?: Record<string, unknown> | null;
}

export interface TaskUpdateRequest {
  description?: string;
  status?: TaskStatus;
  progress?: number;
  priority?: number;
  result?: Record<string, unknown> | null;
  error?: string | null;
}

export interface TaskResponse {
  task_id: UUID;
  user_id: UUID | null;
  worker_id: UUID | null;
  workflow_id: UUID | null;
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

export interface TaskListResponse {
  tasks: TaskResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface TaskFilters {
  status?: TaskStatus;
  limit?: number;
  offset?: number;
}

// =============================================================================
// Worker Types
// =============================================================================

export type WorkerStatus = 'online' | 'offline' | 'busy' | 'idle';

export interface WorkerRegisterRequest {
  machine_id: string;
  machine_name: string;
  tools?: string[];
  system_info?: Record<string, unknown> | null;
}

export interface WorkerUpdateRequest {
  machine_name?: string;
  tools?: string[];
  system_info?: Record<string, unknown> | null;
}

export interface WorkerHeartbeatRequest {
  status: WorkerStatus;
  cpu_percent?: number | null;
  memory_percent?: number | null;
  disk_percent?: number | null;
  tools?: string[] | null;
  current_task_id?: UUID | null;
}

export interface WorkerResponse {
  worker_id: UUID;
  machine_id: string;
  machine_name: string;
  status: WorkerStatus;
  tools: string[];
  system_info: Record<string, unknown> | null;
  cpu_percent: number | null;
  memory_percent: number | null;
  disk_percent: number | null;
  last_heartbeat: string | null;
  registered_at: string;
}

export interface WorkerListResponse {
  workers: WorkerResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface WorkerFilters {
  status?: WorkerStatus;
  limit?: number;
  offset?: number;
}

export interface WorkerTaskAssignment {
  task_id: UUID;
  description: string;
  tool_preference: string | null;
  priority: number;
  workflow_id: UUID | null;
  metadata: Record<string, unknown> | null;
}

export interface WorkerMetrics {
  worker_id: UUID;
  cpu_percent: number | null;
  memory_percent: number | null;
  disk_percent: number | null;
  tasks_completed: number;
  tasks_failed: number;
  average_execution_time_ms: number | null;
  uptime_seconds: number;
}

// =============================================================================
// Workflow Types
// =============================================================================

export type WorkflowStatus =
  | 'draft'
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type NodeStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'waiting';

export type WorkflowType = 'sequential' | 'concurrent' | 'dag';

export interface WorkflowNodeCreateRequest {
  name: string;
  node_type?: string;
  order_index?: number;
  agent_config?: Record<string, unknown> | null;
  condition_config?: Record<string, unknown> | null;
  dependencies?: UUID[] | null;
  max_retries?: number;
}

export interface WorkflowEdgeCreateRequest {
  from_node_id: UUID;
  to_node_id: UUID;
  condition?: Record<string, unknown> | null;
  label?: string | null;
}

export interface WorkflowCreateRequest {
  name: string;
  description?: string | null;
  workflow_type?: WorkflowType;
  nodes?: WorkflowNodeCreateRequest[] | null;
  edges?: WorkflowEdgeCreateRequest[] | null;
  context?: Record<string, unknown> | null;
}

export interface WorkflowUpdateRequest {
  name?: string;
  description?: string | null;
  status?: WorkflowStatus;
  context?: Record<string, unknown> | null;
}

export interface WorkflowNodeResponse {
  node_id: UUID;
  workflow_id: UUID;
  name: string;
  node_type: string;
  status: NodeStatus;
  order_index: number;
  agent_config: Record<string, unknown> | null;
  condition_config: Record<string, unknown> | null;
  dependencies: UUID[] | null;
  input_data: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error: string | null;
  retry_count: number;
  max_retries: number;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface WorkflowEdgeResponse {
  edge_id: UUID;
  workflow_id: UUID;
  from_node_id: UUID;
  to_node_id: UUID;
  condition: Record<string, unknown> | null;
  label: string | null;
}

export interface WorkflowResponse {
  workflow_id: UUID;
  user_id: UUID;
  name: string;
  description: string | null;
  workflow_type: WorkflowType;
  status: WorkflowStatus;
  dag_definition: Record<string, unknown> | null;
  context: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  error: string | null;
  total_nodes: number;
  completed_nodes: number;
  progress: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  nodes?: WorkflowNodeResponse[] | null;
  edges?: WorkflowEdgeResponse[] | null;
}

export interface WorkflowListResponse {
  workflows: WorkflowResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface WorkflowFilters {
  status?: WorkflowStatus;
  limit?: number;
  offset?: number;
}

// Workflow Template Types
export interface WorkflowTemplateMetadata {
  template_id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  required_inputs: string[];
  node_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkflowTemplateDetail extends WorkflowTemplateMetadata {
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
  default_context: Record<string, unknown>;
  workflow_type: WorkflowType;
}

export interface WorkflowTemplateListResponse {
  templates: WorkflowTemplateMetadata[];
  total: number;
}

export interface WorkflowFromTemplateRequest {
  template_id: string;
  input: Record<string, unknown>;
  name?: string | null;
}

// Checkpoint Types
export interface CheckpointCreateRequest {
  name?: string | null;
  description?: string | null;
}

export interface CheckpointResponse {
  checkpoint_id: UUID;
  workflow_id: UUID;
  name: string;
  description: string | null;
  state: Record<string, unknown>;
  node_states: Record<string, unknown>;
  created_at: string;
  created_by: UUID | null;
}

export interface CheckpointListResponse {
  checkpoints: CheckpointResponse[];
  total: number;
}

// Human Review Types
export type ReviewDecision = 'approve' | 'reject' | 'modify';

export interface HumanReviewRequest {
  decision: ReviewDecision;
  comments?: string | null;
  modifications?: Record<string, unknown> | null;
}

export interface HumanReviewResponse {
  node_id: UUID;
  workflow_id: UUID;
  decision: ReviewDecision;
  comments: string | null;
  reviewer_id: UUID;
  reviewed_at: string;
  workflow_status: WorkflowStatus;
}

// Execution Graph Types
export interface ExecutionGraphNode {
  node_id: string;
  name: string;
  node_type: string;
  status: NodeStatus;
  order_index: number;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  error: string | null;
  output_preview: string | null;
}

export interface ExecutionGraphEdge {
  edge_id: string;
  from_node_id: string;
  to_node_id: string;
  label: string | null;
  executed: boolean;
}

export interface ExecutionGraphResponse {
  workflow_id: UUID;
  workflow_name: string;
  workflow_status: WorkflowStatus;
  workflow_type: WorkflowType;
  nodes: ExecutionGraphNode[];
  edges: ExecutionGraphEdge[];
  entry_node: string | null;
  exit_nodes: string[];
  progress: number;
  total_nodes: number;
  completed_nodes: number;
  current_node: string | null;
  started_at: string | null;
  completed_at: string | null;
}

// =============================================================================
// MCP Types
// =============================================================================

export type MCPTransport = 'stdio' | 'sse' | 'websocket';

export interface MCPServerRegisterRequest {
  name: string;
  transport?: MCPTransport;
  command?: string | null;
  args?: string[];
  env?: Record<string, string>;
  url?: string | null;
  timeout?: number;
}

export interface MCPServerStatusResponse {
  name: string;
  status: string;
  connected: boolean;
  tool_count: number;
  connected_at: string | null;
  error: string | null;
}

export interface MCPBusHealthResponse {
  bus_running: boolean;
  total_servers: number;
  connected_servers: number;
  total_tools: number;
  servers: Record<string, unknown>;
}

export interface MCPToolDefinition {
  name: string;
  description: string;
  server: string;
  input_schema: Record<string, unknown>;
}

export interface MCPToolListResponse {
  total: number;
  tools: MCPToolDefinition[];
}

export interface MCPToolInvokeRequest {
  tool_path: string;
  arguments: Record<string, unknown>;
  timeout?: number | null;
}

export interface MCPToolInvokeResponse {
  status: string;
  tool_path: string;
  result: unknown;
  error: string | null;
  execution_time: number;
}
