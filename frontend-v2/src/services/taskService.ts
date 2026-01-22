/**
 * Task Service
 *
 * API service for task CRUD operations and management.
 */

import axios from 'axios';
import { apiClient, tokenStorage, getErrorMessage } from './api';
import type {
  Task,
  TaskCreate,
  TaskUpdate,
  TaskListResponse,
  TaskListParams,
  TaskLog,
} from '../types/task';

// API base URL - defaults to local development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * API Error class with typed response
 */
export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Handle API errors uniformly
 */
function handleApiError(error: unknown): never {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status || 500;
    const detail = error.response?.data?.detail || error.message;
    throw new ApiError(status, detail);
  }
  throw error;
}

/**
 * Task Service API
 */
export const taskService = {
  /**
   * List tasks with optional filters and pagination
   */
  async list(params: TaskListParams = {}): Promise<TaskListResponse> {
    try {
      const queryParams = new URLSearchParams();

      if (params.status) queryParams.append('status', params.status);
      if (params.limit) queryParams.append('limit', params.limit.toString());
      if (params.offset) queryParams.append('offset', params.offset.toString());

      const response = await apiClient.get<TaskListResponse>(
        `/tasks?${queryParams.toString()}`
      );
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Get a single task by ID
   */
  async get(taskId: string): Promise<Task> {
    try {
      const response = await apiClient.get<Task>(`/tasks/${taskId}`);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Create a new task
   */
  async create(data: TaskCreate): Promise<Task> {
    try {
      const response = await apiClient.post<Task>('/tasks', data);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Update an existing task
   */
  async update(taskId: string, data: TaskUpdate): Promise<Task> {
    try {
      const response = await apiClient.put<Task>(`/tasks/${taskId}`, data);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Delete a task
   */
  async delete(taskId: string): Promise<void> {
    try {
      await apiClient.delete(`/tasks/${taskId}`);
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Cancel a running task
   */
  async cancel(taskId: string): Promise<Task> {
    try {
      const response = await apiClient.post<Task>(`/tasks/${taskId}/cancel`);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Retry a failed task
   */
  async retry(taskId: string): Promise<Task> {
    try {
      // Reset status to pending to retry
      const response = await apiClient.put<Task>(`/tasks/${taskId}`, {
        status: 'pending',
        error: null,
        progress: 0,
      });
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Get task logs (placeholder - backend endpoint TBD)
   */
  async getLogs(taskId: string): Promise<TaskLog[]> {
    try {
      // This endpoint may need to be implemented in the backend
      const response = await apiClient.get<TaskLog[]>(`/tasks/${taskId}/logs`);
      return response.data;
    } catch (error) {
      // Return empty array if endpoint doesn't exist yet
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return [];
      }
      handleApiError(error);
    }
  },

  /**
   * Bulk update task status
   */
  async bulkUpdateStatus(
    taskIds: string[],
    status: string
  ): Promise<Task[]> {
    try {
      const results = await Promise.all(
        taskIds.map((id) => taskService.update(id, { status: status as Task['status'] }))
      );
      return results;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Bulk delete tasks
   */
  async bulkDelete(taskIds: string[]): Promise<void> {
    try {
      await Promise.all(taskIds.map((id) => taskService.delete(id)));
    } catch (error) {
      handleApiError(error);
    }
  },
};

/**
 * WebSocket connection for real-time task updates
 */
export class TaskWebSocket {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(
    private taskId: string,
    private onMessage: (data: unknown) => void,
    private onError?: (error: Event) => void
  ) {}

  connect(): void {
    const token = tokenStorage.getAccessToken();
    if (!token) {
      console.error('No auth token for WebSocket connection');
      return;
    }

    const wsUrl = API_BASE_URL.replace('http', 'ws');
    this.socket = new WebSocket(
      `${wsUrl}/api/v1/tasks/${this.taskId}/ws?token=${token}`
    );

    this.socket.onopen = () => {
      console.log(`WebSocket connected for task ${this.taskId}`);
      this.reconnectAttempts = 0;
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.onMessage(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.onError?.(error);
    };

    this.socket.onclose = () => {
      console.log(`WebSocket closed for task ${this.taskId}`);
      this.attemptReconnect();
    };
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(
          `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
        );
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }
}

export default taskService;
