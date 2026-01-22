/**
 * Dashboard API Service
 *
 * API service for dashboard data fetching with React Query hooks.
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { apiClient } from './api';
import {
  TaskListResponse,
  WorkerListResponse,
  WorkflowListResponse,
  MCPBusHealthResponse,
} from '../types/api';
import { Task } from '../types/task';
import { Worker } from '../types/worker';
import { WorkflowResponse } from '../types/api';
import { DashboardStats, SystemHealthStatus, ConnectionStatus } from '../types/dashboard';

// =============================================================================
// Query Keys
// =============================================================================

export const dashboardKeys = {
  all: ['dashboard'] as const,
  stats: () => [...dashboardKeys.all, 'stats'] as const,
  recentTasks: (limit: number) => [...dashboardKeys.all, 'recentTasks', limit] as const,
  workers: () => [...dashboardKeys.all, 'workers'] as const,
  activeWorkflows: (limit: number) => [...dashboardKeys.all, 'activeWorkflows', limit] as const,
  systemHealth: () => [...dashboardKeys.all, 'systemHealth'] as const,
};

// =============================================================================
// API Functions
// =============================================================================

/**
 * Fetch dashboard statistics
 */
export async function fetchDashboardStats(): Promise<DashboardStats> {
  // Fetch data from multiple endpoints in parallel
  const [tasksResponse, workersResponse, workflowsResponse] = await Promise.all([
    apiClient.get<TaskListResponse>('/tasks?limit=1000'),
    apiClient.get<WorkerListResponse>('/workers?limit=100'),
    apiClient.get<WorkflowListResponse>('/workflows?limit=100'),
  ]);

  const tasks = tasksResponse.data.tasks;
  const workers = workersResponse.data.workers;
  const workflows = workflowsResponse.data.workflows;

  // Calculate today's stats
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const completedTasksToday = tasks.filter((t: Task) => {
    if (!t.completed_at) return false;
    const completedDate = new Date(t.completed_at);
    return completedDate >= today && t.status === 'completed';
  }).length;

  const failedTasksToday = tasks.filter((t: Task) => {
    if (!t.completed_at) return false;
    const completedDate = new Date(t.completed_at);
    return completedDate >= today && t.status === 'failed';
  }).length;

  return {
    totalTasks: tasksResponse.data.total,
    totalWorkers: workersResponse.data.total,
    totalWorkflows: workflowsResponse.data.total,
    activeTasks: tasks.filter((t: Task) => t.status === 'running' || t.status === 'pending' || t.status === 'assigned').length,
    activeWorkers: workers.filter((w: Worker) => w.status === 'online' || w.status === 'busy').length,
    activeWorkflows: workflows.filter((w: WorkflowResponse) => w.status === 'running').length,
    completedTasksToday,
    failedTasksToday,
  };
}

/**
 * Fetch recent tasks
 */
export async function fetchRecentTasks(limit: number = 10): Promise<Task[]> {
  const response = await apiClient.get<TaskListResponse>(`/tasks?limit=${limit}&offset=0`);
  return response.data.tasks;
}

/**
 * Fetch all workers
 */
export async function fetchDashboardWorkers(): Promise<Worker[]> {
  const response = await apiClient.get<WorkerListResponse>('/workers?limit=100');
  return response.data.workers;
}

/**
 * Fetch active workflows
 */
export async function fetchActiveWorkflows(limit: number = 5): Promise<WorkflowResponse[]> {
  // Try to get running workflows first, then fall back to all workflows
  try {
    const response = await apiClient.get<WorkflowListResponse>(
      `/workflows?status=running&limit=${limit}&offset=0`
    );
    return response.data.workflows;
  } catch {
    // If status filter is not supported, get all workflows
    const response = await apiClient.get<WorkflowListResponse>(
      `/workflows?limit=${limit}&offset=0`
    );
    return response.data.workflows.filter(w => w.status === 'running' || w.status === 'pending');
  }
}

/**
 * Fetch system health status
 */
export async function fetchSystemHealth(): Promise<SystemHealthStatus> {
  const now = new Date().toISOString();

  // Check backend health
  let backendStatus: SystemHealthStatus['backend'] = {
    status: 'disconnected' as ConnectionStatus,
    latencyMs: null,
    lastChecked: now,
  };

  try {
    const startTime = performance.now();
    await apiClient.get('/health');
    const latency = Math.round(performance.now() - startTime);
    backendStatus = {
      status: 'connected' as ConnectionStatus,
      latencyMs: latency,
      lastChecked: now,
    };
  } catch {
    backendStatus = {
      status: 'error' as ConnectionStatus,
      latencyMs: null,
      lastChecked: now,
    };
  }

  // Check MCP Bus health
  let mcpStatus: SystemHealthStatus['mcpBus'] = {
    status: 'disconnected' as ConnectionStatus,
    connectedServers: 0,
    totalServers: 0,
    totalTools: 0,
    lastChecked: now,
  };

  try {
    const response = await apiClient.get<MCPBusHealthResponse>('/mcp/health');
    const mcpHealth = response.data;
    mcpStatus = {
      status: mcpHealth.bus_running ? 'connected' as ConnectionStatus : 'disconnected' as ConnectionStatus,
      connectedServers: mcpHealth.connected_servers,
      totalServers: mcpHealth.total_servers,
      totalTools: mcpHealth.total_tools,
      lastChecked: now,
    };
  } catch {
    mcpStatus = {
      status: 'error' as ConnectionStatus,
      connectedServers: 0,
      totalServers: 0,
      totalTools: 0,
      lastChecked: now,
    };
  }

  // Redis status (derived from backend health - if backend is up, Redis is likely up)
  const redisStatus: SystemHealthStatus['redis'] = {
    status: backendStatus.status === 'connected' ? 'connected' as ConnectionStatus : 'disconnected' as ConnectionStatus,
    lastChecked: now,
  };

  // WebSocket status (placeholder - managed by WebSocket hook)
  const websocketStatus: SystemHealthStatus['websocket'] = {
    status: 'disconnected' as ConnectionStatus,
    lastChecked: now,
  };

  return {
    backend: backendStatus,
    mcpBus: mcpStatus,
    redis: redisStatus,
    websocket: websocketStatus,
  };
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Hook for fetching dashboard stats
 */
export function useDashboardStats(
  options?: Omit<UseQueryOptions<DashboardStats>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dashboardKeys.stats(),
    queryFn: fetchDashboardStats,
    staleTime: 30000, // 30 seconds
    refetchInterval: 30000, // Auto-refresh every 30 seconds
    ...options,
  });
}

/**
 * Hook for fetching recent tasks
 */
export function useRecentTasks(
  limit: number = 10,
  options?: Omit<UseQueryOptions<Task[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dashboardKeys.recentTasks(limit),
    queryFn: () => fetchRecentTasks(limit),
    staleTime: 15000, // 15 seconds
    refetchInterval: 15000,
    ...options,
  });
}

/**
 * Hook for fetching dashboard workers
 */
export function useDashboardWorkers(
  options?: Omit<UseQueryOptions<Worker[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dashboardKeys.workers(),
    queryFn: fetchDashboardWorkers,
    staleTime: 30000,
    refetchInterval: 30000,
    ...options,
  });
}

/**
 * Hook for fetching active workflows
 */
export function useActiveWorkflows(
  limit: number = 5,
  options?: Omit<UseQueryOptions<WorkflowResponse[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dashboardKeys.activeWorkflows(limit),
    queryFn: () => fetchActiveWorkflows(limit),
    staleTime: 30000,
    refetchInterval: 30000,
    ...options,
  });
}

/**
 * Hook for fetching system health
 */
export function useSystemHealth(
  options?: Omit<UseQueryOptions<SystemHealthStatus>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dashboardKeys.systemHealth(),
    queryFn: fetchSystemHealth,
    staleTime: 10000, // 10 seconds
    refetchInterval: 10000,
    ...options,
  });
}
