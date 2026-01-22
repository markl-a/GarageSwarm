/**
 * Workers API Service
 *
 * Handles worker registration, management, and metrics.
 */

import { get, post } from './api';
import type {
  UUID,
  WorkerRegisterRequest,
  WorkerUpdateRequest,
  WorkerResponse,
  WorkerListResponse,
  WorkerFilters,
  WorkerMetrics,
  WorkerHeartbeatRequest,
  WorkerTaskAssignment,
} from '../types/api';

// =============================================================================
// API Endpoints
// =============================================================================

const WORKERS_ENDPOINTS = {
  BASE: '/workers',
  REGISTER: '/workers/register',
  BY_ID: (id: UUID) => `/workers/${id}`,
  HEARTBEAT: (id: UUID) => `/workers/${id}/heartbeat`,
  PULL_TASK: (id: UUID) => `/workers/${id}/pull-task`,
  TASK_COMPLETE: (id: UUID) => `/workers/${id}/task-complete`,
  TASK_FAILED: (id: UUID) => `/workers/${id}/task-failed`,
  REPORT_RESULT: (id: UUID) => `/workers/${id}/report-result`,
} as const;

// =============================================================================
// Workers Service
// =============================================================================

/**
 * Workers service class for managing worker operations
 */
class WorkersService {
  /**
   * Get a list of workers with optional filtering
   *
   * @param filters - Optional filters for status, pagination
   * @returns Paginated list of workers
   */
  async getWorkers(filters?: WorkerFilters): Promise<WorkerListResponse> {
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

    return get<WorkerListResponse>(WORKERS_ENDPOINTS.BASE, params);
  }

  /**
   * Get a specific worker by ID
   *
   * @param id - Worker UUID
   * @returns Worker details
   */
  async getWorker(id: UUID): Promise<WorkerResponse> {
    return get<WorkerResponse>(WORKERS_ENDPOINTS.BY_ID(id));
  }

  /**
   * Register a new worker or update an existing one
   *
   * If a worker with the same machine_id already exists, it will be updated.
   *
   * @param data - Worker registration data
   * @returns Registered/updated worker
   */
  async registerWorker(data: WorkerRegisterRequest): Promise<WorkerResponse> {
    return post<WorkerResponse>(WORKERS_ENDPOINTS.REGISTER, data);
  }

  /**
   * Update worker information
   *
   * Note: The backend uses heartbeat for most updates.
   * This is a convenience method that registers with updated info.
   *
   * @param id - Worker UUID (used to get machine_id)
   * @param data - Worker update data
   * @returns Updated worker
   */
  async updateWorker(id: UUID, data: WorkerUpdateRequest): Promise<WorkerResponse> {
    // First get the current worker to get machine_id
    const worker = await this.getWorker(id);

    // Register again with updated info
    return this.registerWorker({
      machine_id: worker.machine_id,
      machine_name: data.machine_name || worker.machine_name,
      tools: data.tools || worker.tools,
      system_info: data.system_info || worker.system_info,
    });
  }

  /**
   * Send a heartbeat from a worker
   *
   * @param id - Worker UUID
   * @param data - Heartbeat data with status and metrics
   * @returns Updated worker
   */
  async sendHeartbeat(id: UUID, data: WorkerHeartbeatRequest): Promise<WorkerResponse> {
    return post<WorkerResponse>(WORKERS_ENDPOINTS.HEARTBEAT(id), data);
  }

  /**
   * Get worker metrics
   *
   * Returns computed metrics based on worker's current state and task history.
   * Note: Some metrics may need to be computed client-side or from additional endpoints.
   *
   * @param id - Worker UUID
   * @returns Worker metrics
   */
  async getWorkerMetrics(id: UUID): Promise<WorkerMetrics> {
    // Get the worker's current state
    const worker = await this.getWorker(id);

    // Compute uptime from registration time
    const registeredAt = new Date(worker.registered_at);
    const uptimeSeconds = Math.floor((Date.now() - registeredAt.getTime()) / 1000);

    // Return metrics based on available data
    // Note: Some metrics like tasks_completed would need separate tracking
    return {
      worker_id: worker.worker_id,
      cpu_percent: worker.cpu_percent,
      memory_percent: worker.memory_percent,
      disk_percent: worker.disk_percent,
      tasks_completed: 0, // Would need separate endpoint/tracking
      tasks_failed: 0, // Would need separate endpoint/tracking
      average_execution_time_ms: null, // Would need separate endpoint/tracking
      uptime_seconds: uptimeSeconds,
    };
  }

  /**
   * Pull a task for execution (Pull mode)
   *
   * This is typically called by worker agents, not the dashboard.
   *
   * @param id - Worker UUID
   * @returns Task assignment or null if no tasks available
   */
  async pullTask(id: UUID): Promise<WorkerTaskAssignment | null> {
    return get<WorkerTaskAssignment | null>(WORKERS_ENDPOINTS.PULL_TASK(id));
  }

  /**
   * Report task completion
   *
   * This is typically called by worker agents.
   *
   * @param workerId - Worker UUID
   * @param taskId - Completed task UUID
   * @param result - Task result data
   */
  async reportTaskComplete(
    workerId: UUID,
    taskId: UUID,
    result: Record<string, unknown> = {}
  ): Promise<{ status: string }> {
    return post<{ status: string }>(WORKERS_ENDPOINTS.TASK_COMPLETE(workerId), {
      task_id: taskId,
      result,
    });
  }

  /**
   * Report task failure
   *
   * This is typically called by worker agents.
   *
   * @param workerId - Worker UUID
   * @param taskId - Failed task UUID
   * @param error - Error message
   */
  async reportTaskFailed(
    workerId: UUID,
    taskId: UUID,
    error: string
  ): Promise<{ status: string }> {
    return post<{ status: string }>(WORKERS_ENDPOINTS.TASK_FAILED(workerId), {
      task_id: taskId,
      error,
    });
  }

  // =========================================================================
  // Convenience methods
  // =========================================================================

  /**
   * Get all online workers
   */
  async getOnlineWorkers(limit = 50): Promise<WorkerListResponse> {
    return this.getWorkers({ status: 'online', limit });
  }

  /**
   * Get all idle workers (available for tasks)
   */
  async getIdleWorkers(limit = 50): Promise<WorkerListResponse> {
    return this.getWorkers({ status: 'idle', limit });
  }

  /**
   * Get all busy workers (currently executing tasks)
   */
  async getBusyWorkers(limit = 50): Promise<WorkerListResponse> {
    return this.getWorkers({ status: 'busy', limit });
  }

  /**
   * Get all offline workers
   */
  async getOfflineWorkers(limit = 50): Promise<WorkerListResponse> {
    return this.getWorkers({ status: 'offline', limit });
  }

  /**
   * Check if a worker is available for tasks
   */
  async isWorkerAvailable(id: UUID): Promise<boolean> {
    const worker = await this.getWorker(id);
    return worker.status === 'idle' || worker.status === 'online';
  }

  /**
   * Get workers that support a specific tool
   */
  async getWorkersWithTool(tool: string): Promise<WorkerResponse[]> {
    const response = await this.getWorkers({ limit: 100 });
    return response.workers.filter((w) => w.tools.includes(tool));
  }
}

// =============================================================================
// Export Singleton Instance
// =============================================================================

export const workersService = new WorkersService();

// Export individual functions for convenience
export const getWorkers = workersService.getWorkers.bind(workersService);
export const getWorker = workersService.getWorker.bind(workersService);
export const registerWorker = workersService.registerWorker.bind(workersService);
export const updateWorker = workersService.updateWorker.bind(workersService);
export const getWorkerMetrics = workersService.getWorkerMetrics.bind(workersService);
export const sendHeartbeat = workersService.sendHeartbeat.bind(workersService);
export const pullTask = workersService.pullTask.bind(workersService);

export default workersService;
