import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import type { Worker, ApiResponse, PaginatedResponse } from '@/types';

// Query keys
export const workerKeys = {
  all: ['workers'] as const,
  lists: () => [...workerKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...workerKeys.lists(), filters] as const,
  details: () => [...workerKeys.all, 'detail'] as const,
  detail: (id: string) => [...workerKeys.details(), id] as const,
};

// Fetch all workers
export function useWorkers(filters?: { status?: string; type?: string }) {
  return useQuery({
    queryKey: workerKeys.list(filters ?? {}),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.status) params.append('status', filters.status);
      if (filters?.type) params.append('type', filters.type);

      const response = await api.get<PaginatedResponse<Worker>>(`/workers?${params}`);
      return response.data;
    },
  });
}

// Fetch single worker
export function useWorker(id: string) {
  return useQuery({
    queryKey: workerKeys.detail(id),
    queryFn: async () => {
      const response = await api.get<ApiResponse<Worker>>(`/workers/${id}`);
      return response.data.data;
    },
    enabled: !!id,
  });
}

// Create worker
export function useCreateWorker() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { name: string; type: Worker['type']; capabilities?: string[] }) => {
      const response = await api.post<ApiResponse<Worker>>('/workers', data);
      return response.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workerKeys.lists() });
    },
  });
}

// Update worker
export function useUpdateWorker() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, ...data }: { id: string } & Partial<Worker>) => {
      const response = await api.patch<ApiResponse<Worker>>(`/workers/${id}`, data);
      return response.data.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: workerKeys.lists() });
      queryClient.setQueryData(workerKeys.detail(data.id), data);
    },
  });
}

// Delete worker
export function useDeleteWorker() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/workers/${id}`);
      return id;
    },
    onSuccess: (id) => {
      queryClient.invalidateQueries({ queryKey: workerKeys.lists() });
      queryClient.removeQueries({ queryKey: workerKeys.detail(id) });
    },
  });
}
