/**
 * Worker API Service
 *
 * API client for worker-related endpoints using axios and React Query.
 */

import axios, { AxiosInstance } from 'axios';
import { useQuery, useMutation, useQueryClient, UseQueryOptions } from '@tanstack/react-query';
import {
  Worker,
  WorkerListResponse,
  WorkerFilters,
  WorkerRegisterRequest,
  WorkerFormData,
  WorkerTaskHistoryItem,
  MetricsDataPoint,
  WorkerMetricsSummary,
} from '../types/worker';

// API base URL - configurable via environment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor for auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - could redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Query keys
export const workerKeys = {
  all: ['workers'] as const,
  lists: () => [...workerKeys.all, 'list'] as const,
  list: (filters: WorkerFilters) => [...workerKeys.lists(), filters] as const,
  details: () => [...workerKeys.all, 'detail'] as const,
  detail: (id: string) => [...workerKeys.details(), id] as const,
  metrics: (id: string) => [...workerKeys.detail(id), 'metrics'] as const,
  metricsHistory: (id: string, range: string) => [...workerKeys.metrics(id), 'history', range] as const,
  taskHistory: (id: string) => [...workerKeys.detail(id), 'tasks'] as const,
};

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch list of workers with optional filters and pagination
 */
export async function fetchWorkers(
  filters: WorkerFilters = {},
  limit = 50,
  offset = 0
): Promise<WorkerListResponse> {
  const params = new URLSearchParams();

  if (filters.status && filters.status !== 'all') {
    params.append('status', filters.status);
  }
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());

  const response = await apiClient.get<WorkerListResponse>(`/workers?${params.toString()}`);
  return response.data;
}

/**
 * Fetch a single worker by ID
 */
export async function fetchWorker(workerId: string): Promise<Worker> {
  const response = await apiClient.get<Worker>(`/workers/${workerId}`);
  return response.data;
}

/**
 * Register a new worker
 */
export async function registerWorker(data: WorkerRegisterRequest): Promise<Worker> {
  const response = await apiClient.post<Worker>('/workers/register', data);
  return response.data;
}

/**
 * Update worker details
 */
export async function updateWorker(workerId: string, data: Partial<WorkerFormData>): Promise<Worker> {
  const response = await apiClient.patch<Worker>(`/workers/${workerId}`, data);
  return response.data;
}

/**
 * Delete a worker
 */
export async function deleteWorker(workerId: string): Promise<void> {
  await apiClient.delete(`/workers/${workerId}`);
}

/**
 * Activate a worker
 */
export async function activateWorker(workerId: string): Promise<Worker> {
  const response = await apiClient.post<Worker>(`/workers/${workerId}/activate`);
  return response.data;
}

/**
 * Deactivate a worker
 */
export async function deactivateWorker(workerId: string): Promise<Worker> {
  const response = await apiClient.post<Worker>(`/workers/${workerId}/deactivate`);
  return response.data;
}

/**
 * Fetch worker metrics summary
 */
export async function fetchWorkerMetrics(workerId: string): Promise<WorkerMetricsSummary> {
  const response = await apiClient.get<WorkerMetricsSummary>(`/workers/${workerId}/metrics`);
  return response.data;
}

/**
 * Fetch worker metrics history
 */
export async function fetchWorkerMetricsHistory(
  workerId: string,
  range: '1h' | '24h' | '7d' = '24h'
): Promise<MetricsDataPoint[]> {
  const response = await apiClient.get<MetricsDataPoint[]>(
    `/workers/${workerId}/metrics/history?range=${range}`
  );
  return response.data;
}

/**
 * Fetch worker task history
 */
export async function fetchWorkerTaskHistory(
  workerId: string,
  limit = 20,
  offset = 0
): Promise<{ tasks: WorkerTaskHistoryItem[]; total: number }> {
  const response = await apiClient.get<{ tasks: WorkerTaskHistoryItem[]; total: number }>(
    `/workers/${workerId}/tasks?limit=${limit}&offset=${offset}`
  );
  return response.data;
}

/**
 * Bulk activate workers
 */
export async function bulkActivateWorkers(workerIds: string[]): Promise<void> {
  await apiClient.post('/workers/bulk/activate', { worker_ids: workerIds });
}

/**
 * Bulk deactivate workers
 */
export async function bulkDeactivateWorkers(workerIds: string[]): Promise<void> {
  await apiClient.post('/workers/bulk/deactivate', { worker_ids: workerIds });
}

/**
 * Bulk delete workers
 */
export async function bulkDeleteWorkers(workerIds: string[]): Promise<void> {
  await apiClient.post('/workers/bulk/delete', { worker_ids: workerIds });
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Hook for fetching worker list
 */
export function useWorkers(
  filters: WorkerFilters = {},
  limit = 50,
  offset = 0,
  options?: Omit<UseQueryOptions<WorkerListResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: workerKeys.list(filters),
    queryFn: () => fetchWorkers(filters, limit, offset),
    staleTime: 30000, // 30 seconds
    refetchInterval: 30000, // Auto-refresh every 30 seconds
    ...options,
  });
}

/**
 * Hook for fetching a single worker
 */
export function useWorker(
  workerId: string,
  options?: Omit<UseQueryOptions<Worker>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: workerKeys.detail(workerId),
    queryFn: () => fetchWorker(workerId),
    enabled: !!workerId,
    staleTime: 30000,
    refetchInterval: 30000,
    ...options,
  });
}

/**
 * Hook for fetching worker metrics summary
 */
export function useWorkerMetrics(
  workerId: string,
  options?: Omit<UseQueryOptions<WorkerMetricsSummary>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: workerKeys.metrics(workerId),
    queryFn: () => fetchWorkerMetrics(workerId),
    enabled: !!workerId,
    staleTime: 60000, // 1 minute
    refetchInterval: 60000,
    ...options,
  });
}

/**
 * Hook for fetching worker metrics history
 */
export function useWorkerMetricsHistory(
  workerId: string,
  range: '1h' | '24h' | '7d' = '24h',
  options?: Omit<UseQueryOptions<MetricsDataPoint[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: workerKeys.metricsHistory(workerId, range),
    queryFn: () => fetchWorkerMetricsHistory(workerId, range),
    enabled: !!workerId,
    staleTime: 60000,
    refetchInterval: 60000,
    ...options,
  });
}

/**
 * Hook for fetching worker task history
 */
export function useWorkerTaskHistory(
  workerId: string,
  limit = 20,
  offset = 0,
  options?: Omit<UseQueryOptions<{ tasks: WorkerTaskHistoryItem[]; total: number }>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: workerKeys.taskHistory(workerId),
    queryFn: () => fetchWorkerTaskHistory(workerId, limit, offset),
    enabled: !!workerId,
    staleTime: 30000,
    ...options,
  });
}

/**
 * Hook for registering a new worker
 */
export function useRegisterWorker() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: registerWorker,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workerKeys.lists() });
    },
  });
}

/**
 * Hook for updating a worker
 */
export function useUpdateWorker() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ workerId, data }: { workerId: string; data: Partial<WorkerFormData> }) =>
      updateWorker(workerId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: workerKeys.detail(variables.workerId) });
      queryClient.invalidateQueries({ queryKey: workerKeys.lists() });
    },
  });
}

/**
 * Hook for deleting a worker
 */
export function useDeleteWorker() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteWorker,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workerKeys.lists() });
    },
  });
}

/**
 * Hook for activating a worker
 */
export function useActivateWorker() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: activateWorker,
    onSuccess: (_, workerId) => {
      queryClient.invalidateQueries({ queryKey: workerKeys.detail(workerId) });
      queryClient.invalidateQueries({ queryKey: workerKeys.lists() });
    },
  });
}

/**
 * Hook for deactivating a worker
 */
export function useDeactivateWorker() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deactivateWorker,
    onSuccess: (_, workerId) => {
      queryClient.invalidateQueries({ queryKey: workerKeys.detail(workerId) });
      queryClient.invalidateQueries({ queryKey: workerKeys.lists() });
    },
  });
}

/**
 * Hook for bulk actions
 */
export function useBulkWorkerAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ action, workerIds }: { action: 'activate' | 'deactivate' | 'delete'; workerIds: string[] }) => {
      switch (action) {
        case 'activate':
          return bulkActivateWorkers(workerIds);
        case 'deactivate':
          return bulkDeactivateWorkers(workerIds);
        case 'delete':
          return bulkDeleteWorkers(workerIds);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workerKeys.all });
    },
  });
}

export default apiClient;
