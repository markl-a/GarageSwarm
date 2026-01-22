// Worker types
export interface Worker {
  id: string;
  name: string;
  type: 'desktop' | 'docker' | 'mobile';
  status: 'online' | 'offline' | 'busy';
  capabilities: string[];
  lastHeartbeat: string;
  createdAt: string;
  updatedAt: string;
}

// Task types
export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'assigned' | 'running' | 'completed' | 'failed' | 'cancelled';
  tool: 'claude_code' | 'gemini_cli' | 'ollama';
  workerId?: string;
  result?: string;
  error?: string;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
}

// Workflow types
export interface WorkflowNode {
  id: string;
  type: 'task' | 'condition' | 'parallel' | 'loop';
  data: {
    label: string;
    taskId?: string;
    condition?: string;
  };
  position: { x: number; y: number };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  status: 'draft' | 'active' | 'paused' | 'completed' | 'failed';
  createdAt: string;
  updatedAt: string;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Auth types
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

// Re-export WebSocket types
export * from './websocket';

// Re-export detailed Workflow types
export * from './workflow';
