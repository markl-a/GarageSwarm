import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import type { Task, ApiResponse, PaginatedResponse } from '@/types';

// Query keys
export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...taskKeys.lists(), filters] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
};

// Fetch all tasks
export function useTasks(filters?: { status?: string; tool?: string; workerId?: string }) {
  return useQuery({
    queryKey: taskKeys.list(filters ?? {}),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.status) params.append('status', filters.status);
      if (filters?.tool) params.append('tool', filters.tool);
      if (filters?.workerId) params.append('worker_id', filters.workerId);

      const response = await api.get<PaginatedResponse<Task>>(`/tasks?${params}`);
      return response.data;
    },
  });
}

// Fetch single task
export function useTask(id: string) {
  return useQuery({
    queryKey: taskKeys.detail(id),
    queryFn: async () => {
      const response = await api.get<ApiResponse<Task>>(`/tasks/${id}`);
      return response.data.data;
    },
    enabled: !!id,
  });
}

// Create task
export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      title: string;
      description: string;
      tool: Task['tool'];
      workerId?: string
    }) => {
      const response = await api.post<ApiResponse<Task>>('/tasks', data);
      return response.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}

// Update task
export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, ...data }: { id: string } & Partial<Task>) => {
      const response = await api.patch<ApiResponse<Task>>(`/tasks/${id}`, data);
      return response.data.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.setQueryData(taskKeys.detail(data.id), data);
    },
  });
}

// Cancel task
export function useCancelTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ApiResponse<Task>>(`/tasks/${id}/cancel`);
      return response.data.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.setQueryData(taskKeys.detail(data.id), data);
    },
  });
}

// Retry failed task
export function useRetryTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ApiResponse<Task>>(`/tasks/${id}/retry`);
      return response.data.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.setQueryData(taskKeys.detail(data.id), data);
    },
  });
}

// Delete task
export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/tasks/${id}`);
      return id;
    },
    onSuccess: (id) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.removeQueries({ queryKey: taskKeys.detail(id) });
    },
  });
}
