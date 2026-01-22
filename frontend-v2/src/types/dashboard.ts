/**
 * Dashboard Types
 *
 * TypeScript type definitions for dashboard-specific data.
 */

import {
  TaskResponse,
  WorkerResponse,
  WorkflowResponse,
  MCPBusHealthResponse,
} from './api';

// =============================================================================
// Dashboard Stats Types
// =============================================================================

export interface DashboardStats {
  totalTasks: number;
  totalWorkers: number;
  totalWorkflows: number;
  activeTasks: number;
  activeWorkers: number;
  activeWorkflows: number;
  completedTasksToday: number;
  failedTasksToday: number;
}

export interface StatChange {
  value: number;
  direction: 'up' | 'down' | 'neutral';
  percentage: number;
}

export interface DashboardStatsWithChange extends DashboardStats {
  taskChange: StatChange;
  workerChange: StatChange;
  workflowChange: StatChange;
}

// =============================================================================
// System Health Types
// =============================================================================

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

export interface SystemHealthStatus {
  backend: {
    status: ConnectionStatus;
    latencyMs: number | null;
    lastChecked: string;
  };
  mcpBus: {
    status: ConnectionStatus;
    connectedServers: number;
    totalServers: number;
    totalTools: number;
    lastChecked: string;
  };
  redis: {
    status: ConnectionStatus;
    lastChecked: string;
  };
  websocket: {
    status: ConnectionStatus;
    lastChecked: string;
  };
}

// =============================================================================
// Dashboard Data Types
// =============================================================================

export interface DashboardData {
  stats: DashboardStats;
  recentTasks: TaskResponse[];
  workers: WorkerResponse[];
  activeWorkflows: WorkflowResponse[];
  systemHealth: SystemHealthStatus;
}

// =============================================================================
// Component Props Types
// =============================================================================

export interface StatsCardProps {
  icon: React.ReactNode;
  title: string;
  value: string | number;
  change?: StatChange;
  loading?: boolean;
}

export interface RecentTasksProps {
  tasks: TaskResponse[];
  loading?: boolean;
  onTaskClick?: (taskId: string) => void;
}

export interface WorkerGridProps {
  workers: WorkerResponse[];
  loading?: boolean;
  onWorkerClick?: (workerId: string) => void;
}

export interface ActiveWorkflowsProps {
  workflows: WorkflowResponse[];
  loading?: boolean;
  onWorkflowClick?: (workflowId: string) => void;
}

export interface SystemHealthProps {
  health: SystemHealthStatus;
  loading?: boolean;
}
