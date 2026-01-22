/**
 * Workflows API Service
 *
 * Handles workflow CRUD, execution management, templates,
 * checkpoints, and human review operations.
 */

import { get, post, put, del } from './api';
import type {
  UUID,
  WorkflowCreateRequest,
  WorkflowUpdateRequest,
  WorkflowResponse,
  WorkflowListResponse,
  WorkflowFilters,
  WorkflowTemplateMetadata,
  WorkflowTemplateDetail,
  WorkflowTemplateListResponse,
  WorkflowFromTemplateRequest,
  CheckpointCreateRequest,
  CheckpointResponse,
  CheckpointListResponse,
  HumanReviewRequest,
  HumanReviewResponse,
  ExecutionGraphResponse,
} from '../types/api';

// =============================================================================
// API Endpoints
// =============================================================================

const WORKFLOWS_ENDPOINTS = {
  BASE: '/workflows',
  BY_ID: (id: UUID) => `/workflows/${id}`,
  EXECUTE: (id: UUID) => `/workflows/${id}/execute`,
  PAUSE: (id: UUID) => `/workflows/${id}/pause`,
  RESUME: (id: UUID) => `/workflows/${id}/resume`,
  CANCEL: (id: UUID) => `/workflows/${id}/cancel`,
  TEMPLATES: '/workflows/templates',
  TEMPLATE_BY_ID: (id: string) => `/workflows/templates/${id}`,
  FROM_TEMPLATE: '/workflows/from-template',
  CHECKPOINT: (id: UUID) => `/workflows/${id}/checkpoint`,
  CHECKPOINTS: (id: UUID) => `/workflows/${id}/checkpoints`,
  RESTORE: (workflowId: UUID, checkpointId: UUID) =>
    `/workflows/${workflowId}/restore/${checkpointId}`,
  REVIEW: (workflowId: UUID, nodeId: UUID) =>
    `/workflows/${workflowId}/nodes/${nodeId}/review`,
  EXECUTION_GRAPH: (id: UUID) => `/workflows/${id}/execution-graph`,
} as const;

// =============================================================================
// Workflows Service
// =============================================================================

/**
 * Workflows service class for managing workflow operations
 */
class WorkflowsService {
  // =========================================================================
  // Basic CRUD Operations
  // =========================================================================

  /**
   * Get a list of workflows with optional filtering
   *
   * @param filters - Optional filters for status, pagination
   * @returns Paginated list of workflows
   */
  async getWorkflows(filters?: WorkflowFilters): Promise<WorkflowListResponse> {
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

    return get<WorkflowListResponse>(WORKFLOWS_ENDPOINTS.BASE, params);
  }

  /**
   * Get a specific workflow by ID with nodes and edges
   *
   * @param id - Workflow UUID
   * @returns Workflow details including nodes and edges
   */
  async getWorkflow(id: UUID): Promise<WorkflowResponse> {
    return get<WorkflowResponse>(WORKFLOWS_ENDPOINTS.BY_ID(id));
  }

  /**
   * Create a new workflow
   *
   * @param data - Workflow creation data including nodes and edges
   * @returns Created workflow
   */
  async createWorkflow(data: WorkflowCreateRequest): Promise<WorkflowResponse> {
    return post<WorkflowResponse>(WORKFLOWS_ENDPOINTS.BASE, data);
  }

  /**
   * Update an existing workflow
   *
   * Only allowed when workflow is in 'draft' or 'failed' state.
   *
   * @param id - Workflow UUID
   * @param data - Workflow update data
   * @returns Updated workflow
   */
  async updateWorkflow(id: UUID, data: WorkflowUpdateRequest): Promise<WorkflowResponse> {
    return put<WorkflowResponse>(WORKFLOWS_ENDPOINTS.BY_ID(id), data);
  }

  /**
   * Delete a workflow
   *
   * Cannot delete running workflows.
   *
   * @param id - Workflow UUID
   */
  async deleteWorkflow(id: UUID): Promise<void> {
    await del(WORKFLOWS_ENDPOINTS.BY_ID(id));
  }

  // =========================================================================
  // Execution Control
  // =========================================================================

  /**
   * Start workflow execution
   *
   * Only works for workflows in 'draft' or 'failed' state.
   *
   * @param id - Workflow UUID
   * @returns Workflow with updated status
   */
  async startWorkflow(id: UUID): Promise<WorkflowResponse> {
    return post<WorkflowResponse>(WORKFLOWS_ENDPOINTS.EXECUTE(id));
  }

  /**
   * Pause a running workflow
   *
   * @param id - Workflow UUID
   * @returns Paused workflow
   */
  async pauseWorkflow(id: UUID): Promise<WorkflowResponse> {
    return post<WorkflowResponse>(WORKFLOWS_ENDPOINTS.PAUSE(id));
  }

  /**
   * Resume a paused workflow
   *
   * @param id - Workflow UUID
   * @returns Resumed workflow
   */
  async resumeWorkflow(id: UUID): Promise<WorkflowResponse> {
    return post<WorkflowResponse>(WORKFLOWS_ENDPOINTS.RESUME(id));
  }

  /**
   * Cancel a workflow
   *
   * Cannot cancel completed or already cancelled workflows.
   *
   * @param id - Workflow UUID
   * @returns Cancelled workflow
   */
  async cancelWorkflow(id: UUID): Promise<WorkflowResponse> {
    return post<WorkflowResponse>(WORKFLOWS_ENDPOINTS.CANCEL(id));
  }

  // =========================================================================
  // Template Operations
  // =========================================================================

  /**
   * Get available workflow templates
   *
   * @param category - Optional category filter
   * @param tag - Optional tag filter
   * @returns List of template metadata
   */
  async getTemplates(
    category?: string,
    tag?: string
  ): Promise<WorkflowTemplateListResponse> {
    const params: Record<string, unknown> = {};
    if (category) params.category = category;
    if (tag) params.tag = tag;

    return get<WorkflowTemplateListResponse>(WORKFLOWS_ENDPOINTS.TEMPLATES, params);
  }

  /**
   * Get detailed template information
   *
   * @param templateId - Template identifier
   * @returns Detailed template with nodes and edges
   */
  async getTemplate(templateId: string): Promise<WorkflowTemplateDetail> {
    return get<WorkflowTemplateDetail>(WORKFLOWS_ENDPOINTS.TEMPLATE_BY_ID(templateId));
  }

  /**
   * Create a workflow from a template
   *
   * @param templateId - Template identifier
   * @param input - Input parameters for template variables
   * @param name - Optional workflow name override
   * @returns Created workflow
   */
  async createFromTemplate(
    templateId: string,
    input: Record<string, unknown>,
    name?: string
  ): Promise<WorkflowResponse> {
    const data: WorkflowFromTemplateRequest = {
      template_id: templateId,
      input,
      name,
    };
    return post<WorkflowResponse>(WORKFLOWS_ENDPOINTS.FROM_TEMPLATE, data);
  }

  // =========================================================================
  // Checkpoint Operations
  // =========================================================================

  /**
   * Create a manual checkpoint for workflow state
   *
   * @param workflowId - Workflow UUID
   * @param name - Optional checkpoint name
   * @param description - Optional description
   * @returns Created checkpoint
   */
  async createCheckpoint(
    workflowId: UUID,
    name?: string,
    description?: string
  ): Promise<CheckpointResponse> {
    const data: CheckpointCreateRequest = { name, description };
    return post<CheckpointResponse>(WORKFLOWS_ENDPOINTS.CHECKPOINT(workflowId), data);
  }

  /**
   * Get all checkpoints for a workflow
   *
   * @param workflowId - Workflow UUID
   * @returns List of checkpoints
   */
  async getCheckpoints(workflowId: UUID): Promise<CheckpointListResponse> {
    return get<CheckpointListResponse>(WORKFLOWS_ENDPOINTS.CHECKPOINTS(workflowId));
  }

  /**
   * Restore workflow state from a checkpoint
   *
   * Only works on paused, failed, or cancelled workflows.
   *
   * @param workflowId - Workflow UUID
   * @param checkpointId - Checkpoint UUID to restore from
   * @returns Restored workflow
   */
  async restoreFromCheckpoint(
    workflowId: UUID,
    checkpointId: UUID
  ): Promise<WorkflowResponse> {
    return post<WorkflowResponse>(
      WORKFLOWS_ENDPOINTS.RESTORE(workflowId, checkpointId)
    );
  }

  // =========================================================================
  // Human Review Operations
  // =========================================================================

  /**
   * Submit a human review decision for a workflow node
   *
   * @param workflowId - Workflow UUID
   * @param nodeId - Node UUID waiting for review
   * @param decision - Review decision (approve, reject, modify)
   * @param comments - Optional reviewer comments
   * @param modifications - Optional state modifications (for 'modify' decision)
   * @returns Review response with updated workflow status
   */
  async submitReview(
    workflowId: UUID,
    nodeId: UUID,
    decision: 'approve' | 'reject' | 'modify',
    comments?: string,
    modifications?: Record<string, unknown>
  ): Promise<HumanReviewResponse> {
    const data: HumanReviewRequest = {
      decision,
      comments,
      modifications,
    };
    return post<HumanReviewResponse>(
      WORKFLOWS_ENDPOINTS.REVIEW(workflowId, nodeId),
      data
    );
  }

  // =========================================================================
  // Visualization
  // =========================================================================

  /**
   * Get execution graph data for visualization
   *
   * Returns node and edge data formatted for graph libraries.
   *
   * @param workflowId - Workflow UUID
   * @returns Execution graph with nodes, edges, and progress info
   */
  async getExecutionGraph(workflowId: UUID): Promise<ExecutionGraphResponse> {
    return get<ExecutionGraphResponse>(WORKFLOWS_ENDPOINTS.EXECUTION_GRAPH(workflowId));
  }

  // =========================================================================
  // Convenience Methods
  // =========================================================================

  /**
   * Get all draft workflows
   */
  async getDraftWorkflows(limit = 50): Promise<WorkflowListResponse> {
    return this.getWorkflows({ status: 'draft', limit });
  }

  /**
   * Get all running workflows
   */
  async getRunningWorkflows(limit = 50): Promise<WorkflowListResponse> {
    return this.getWorkflows({ status: 'running', limit });
  }

  /**
   * Get all completed workflows
   */
  async getCompletedWorkflows(limit = 50): Promise<WorkflowListResponse> {
    return this.getWorkflows({ status: 'completed', limit });
  }

  /**
   * Get all failed workflows
   */
  async getFailedWorkflows(limit = 50): Promise<WorkflowListResponse> {
    return this.getWorkflows({ status: 'failed', limit });
  }

  /**
   * Get all paused workflows
   */
  async getPausedWorkflows(limit = 50): Promise<WorkflowListResponse> {
    return this.getWorkflows({ status: 'paused', limit });
  }

  /**
   * Create a simple sequential workflow
   */
  async createSequentialWorkflow(
    name: string,
    nodeNames: string[],
    toolPreference = 'claude_code'
  ): Promise<WorkflowResponse> {
    const nodes = nodeNames.map((nodeName, index) => ({
      name: nodeName,
      node_type: 'task',
      order_index: index,
      agent_config: { tool: toolPreference },
    }));

    return this.createWorkflow({
      name,
      workflow_type: 'sequential',
      nodes,
    });
  }

  /**
   * Approve a review node
   */
  async approveReview(
    workflowId: UUID,
    nodeId: UUID,
    comments?: string
  ): Promise<HumanReviewResponse> {
    return this.submitReview(workflowId, nodeId, 'approve', comments);
  }

  /**
   * Reject a review node
   */
  async rejectReview(
    workflowId: UUID,
    nodeId: UUID,
    comments: string
  ): Promise<HumanReviewResponse> {
    return this.submitReview(workflowId, nodeId, 'reject', comments);
  }
}

// =============================================================================
// Export Singleton Instance
// =============================================================================

export const workflowsService = new WorkflowsService();

// Export individual functions for convenience
export const getWorkflows = workflowsService.getWorkflows.bind(workflowsService);
export const getWorkflow = workflowsService.getWorkflow.bind(workflowsService);
export const createWorkflow = workflowsService.createWorkflow.bind(workflowsService);
export const updateWorkflow = workflowsService.updateWorkflow.bind(workflowsService);
export const deleteWorkflow = workflowsService.deleteWorkflow.bind(workflowsService);
export const startWorkflow = workflowsService.startWorkflow.bind(workflowsService);
export const pauseWorkflow = workflowsService.pauseWorkflow.bind(workflowsService);
export const resumeWorkflow = workflowsService.resumeWorkflow.bind(workflowsService);
export const cancelWorkflow = workflowsService.cancelWorkflow.bind(workflowsService);
export const getTemplates = workflowsService.getTemplates.bind(workflowsService);
export const createFromTemplate = workflowsService.createFromTemplate.bind(workflowsService);
export const getExecutionGraph = workflowsService.getExecutionGraph.bind(workflowsService);
export const submitReview = workflowsService.submitReview.bind(workflowsService);

export default workflowsService;
