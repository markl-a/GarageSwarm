/**
 * Tasks API Service
 *
 * Handles task CRUD operations and management.
 */

import { get, post, put, del } from './api';
import type {
  UUID,
  TaskCreateRequest,
  TaskUpdateRequest,
  TaskResponse,
  TaskListResponse,
  TaskFilters,
} from '../types/api';

// =============================================================================
// API Endpoints
// =============================================================================

const TASKS_ENDPOINTS = {
  BASE: '/tasks',
  BY_ID: (id: UUID) => `/tasks/${id}`,
  CANCEL: (id: UUID) => `/tasks/${id}/cancel`,
} as const;

// =============================================================================
// Tasks Service
// =============================================================================

/**
 * Tasks service class for managing task operations
 */
class TasksService {
  /**
   * Get a list of tasks with optional filtering
   *
   * @param filters - Optional filters for status, pagination
   * @returns Paginated list of tasks
   */
  async getTasks(filters?: TaskFilters): Promise<TaskListResponse> {
    const params: Record<string, unknown> = {};

    if (filters?.status) {
      params.status = filters.status;
    }
    if (filters?.limit !== undefined) {
      params.limit = filters.limit;
    }
    if (filters?.offset !== undefined) {
      params.offset = filters.offset;
    }

    return get<TaskListResponse>(TASKS_ENDPOINTS.BASE, params);
  }

  /**
   * Get a specific task by ID
   *
   * @param id - Task UUID
   * @returns Task details
   */
  async getTask(id: UUID): Promise<TaskResponse> {
    return get<TaskResponse>(TASKS_ENDPOINTS.BY_ID(id));
  }

  /**
   * Create a new task
   *
   * @param data - Task creation data
   * @returns Created task
   */
  async createTask(data: TaskCreateRequest): Promise<TaskResponse> {
    return post<TaskResponse>(TASKS_ENDPOINTS.BASE, data);
  }

  /**
   * Update an existing task
   *
   * @param id - Task UUID
   * @param data - Task update data
   * @returns Updated task
   */
  async updateTask(id: UUID, data: TaskUpdateRequest): Promise<TaskResponse> {
    return put<TaskResponse>(TASKS_ENDPOINTS.BY_ID(id), data);
  }

  /**
   * Delete a task
   *
   * @param id - Task UUID
   */
  async deleteTask(id: UUID): Promise<void> {
    await del(TASKS_ENDPOINTS.BY_ID(id));
  }

  /**
   * Cancel a running task
   *
   * @param id - Task UUID
   * @returns Cancelled task
   */
  async cancelTask(id: UUID): Promise<TaskResponse> {
    return post<TaskResponse>(TASKS_ENDPOINTS.CANCEL(id));
  }

  /**
   * Assign a task to a worker
   *
   * This is typically done automatically by the backend,
   * but can be forced via task update.
   *
   * @param taskId - Task UUID
   * @param workerId - Worker UUID to assign
   * @returns Updated task
   */
  async assignTask(taskId: UUID, workerId: UUID): Promise<TaskResponse> {
    return put<TaskResponse>(TASKS_ENDPOINTS.BY_ID(taskId), {
      status: 'assigned',
      // Note: The backend may handle worker assignment differently
      // This is a simplified version that updates status
    });
  }

  // =========================================================================
  // Convenience methods
  // =========================================================================

  /**
   * Get all pending tasks
   */
  async getPendingTasks(limit = 50): Promise<TaskListResponse> {
    return this.getTasks({ status: 'pending', limit });
  }

  /**
   * Get all running tasks
   */
  async getRunningTasks(limit = 50): Promise<TaskListResponse> {
    return this.getTasks({ status: 'running', limit });
  }

  /**
   * Get all completed tasks
   */
  async getCompletedTasks(limit = 50): Promise<TaskListResponse> {
    return this.getTasks({ status: 'completed', limit });
  }

  /**
   * Get all failed tasks
   */
  async getFailedTasks(limit = 50): Promise<TaskListResponse> {
    return this.getTasks({ status: 'failed', limit });
  }

  /**
   * Create a quick task with just a description
   */
  async createQuickTask(description: string): Promise<TaskResponse> {
    return this.createTask({ description });
  }

  /**
   * Create a task with a specific tool preference
   */
  async createTaskWithTool(
    description: string,
    tool: string,
    priority = 5
  ): Promise<TaskResponse> {
    return this.createTask({
      description,
      tool_preference: tool,
      priority,
    });
  }
}

// =============================================================================
// Export Singleton Instance
// =============================================================================

export const tasksService = new TasksService();

// Export individual functions for convenience
export const getTasks = tasksService.getTasks.bind(tasksService);
export const getTask = tasksService.getTask.bind(tasksService);
export const createTask = tasksService.createTask.bind(tasksService);
export const updateTask = tasksService.updateTask.bind(tasksService);
export const deleteTask = tasksService.deleteTask.bind(tasksService);
export const cancelTask = tasksService.cancelTask.bind(tasksService);
export const assignTask = tasksService.assignTask.bind(tasksService);

export default tasksService;
