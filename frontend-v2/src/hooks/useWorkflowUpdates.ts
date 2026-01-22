/**
 * useWorkflowUpdates Hook
 *
 * Hook for subscribing to real-time workflow updates via WebSocket.
 * Tracks workflow status, node updates, human review requests, and completions.
 */

import { useEffect, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import websocketService from '../services/websocket';
import { useWebSocketChannels } from './useWebSocket';
import { useNotificationStore } from '../stores/notificationStore';
import {
  WS_EVENTS,
  WorkflowStatus,
  NodeStatus,
  WorkflowCreatedPayload,
  WorkflowUpdatedPayload,
  WorkflowDeletedPayload,
  WorkflowStatusChangedPayload,
  WorkflowNodeUpdatedPayload,
  WorkflowReviewRequestedPayload,
  WorkflowCompletedPayload,
  WorkflowFailedPayload,
  WorkflowBase,
  WorkflowNode,
  HumanReviewRequest,
  NotificationType,
  NotificationCategory,
  ConnectionState,
} from '../types/websocket';

// ============================================================================
// Types
// ============================================================================

export interface WorkflowUpdateCallbacks {
  onWorkflowCreated?: (payload: WorkflowCreatedPayload) => void;
  onWorkflowUpdated?: (payload: WorkflowUpdatedPayload) => void;
  onWorkflowDeleted?: (payload: WorkflowDeletedPayload) => void;
  onWorkflowStatusChanged?: (payload: WorkflowStatusChangedPayload) => void;
  onWorkflowNodeUpdated?: (payload: WorkflowNodeUpdatedPayload) => void;
  onWorkflowReviewRequested?: (payload: WorkflowReviewRequestedPayload) => void;
  onWorkflowCompleted?: (payload: WorkflowCompletedPayload) => void;
  onWorkflowFailed?: (payload: WorkflowFailedPayload) => void;
}

export interface UseWorkflowUpdatesOptions {
  /** Subscribe to specific workflow ID */
  workflowId?: string;
  /** Enable notifications for workflow events */
  enableNotifications?: boolean;
  /** Enable React Query cache updates */
  enableCacheUpdates?: boolean;
  /** Custom callbacks for workflow events */
  callbacks?: WorkflowUpdateCallbacks;
  /** Enable the hook */
  enabled?: boolean;
}

export interface UseWorkflowUpdatesReturn {
  /** List of pending human review requests */
  pendingReviews: HumanReviewRequest[];
  /** Map of workflow node statuses by workflow ID -> node ID -> status */
  nodeStatuses: Map<string, Map<string, NodeStatus>>;
  /** Subscribe to a specific workflow's updates */
  subscribeToWorkflow: (workflowId: string) => () => void;
  /** Unsubscribe from a specific workflow's updates */
  unsubscribeFromWorkflow: (workflowId: string) => void;
  /** Clear a review request after handling */
  clearReviewRequest: (reviewId: string) => void;
  /** Get node status for a specific workflow and node */
  getNodeStatus: (workflowId: string, nodeId: string) => NodeStatus | undefined;
}

// ============================================================================
// Query Keys
// ============================================================================

export const WORKFLOW_QUERY_KEYS = {
  all: ['workflows'] as const,
  lists: () => [...WORKFLOW_QUERY_KEYS.all, 'list'] as const,
  list: (filters: Record<string, unknown>) =>
    [...WORKFLOW_QUERY_KEYS.lists(), filters] as const,
  details: () => [...WORKFLOW_QUERY_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...WORKFLOW_QUERY_KEYS.details(), id] as const,
  nodes: (id: string) => [...WORKFLOW_QUERY_KEYS.detail(id), 'nodes'] as const,
  reviews: () => [...WORKFLOW_QUERY_KEYS.all, 'reviews'] as const,
};

// ============================================================================
// Hook Implementation
// ============================================================================

export function useWorkflowUpdates(
  options: UseWorkflowUpdatesOptions = {}
): UseWorkflowUpdatesReturn {
  const {
    workflowId,
    enableNotifications = true,
    enableCacheUpdates = true,
    callbacks = {},
    enabled = true,
  } = options;

  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((state) => state.addNotification);

  // State for reviews and node statuses
  const [pendingReviews, setPendingReviews] = useState<HumanReviewRequest[]>([]);
  const [nodeStatuses, setNodeStatuses] = useState<
    Map<string, Map<string, NodeStatus>>
  >(new Map());

  // Subscribe to the workflows channel
  useWebSocketChannels(
    workflowId ? `workflow:${workflowId}` : 'workflows',
    enabled
  );

  // ============================================================================
  // Cache Update Helpers
  // ============================================================================

  const updateWorkflowInCache = useCallback(
    (workflow: Partial<WorkflowBase> & { id: string }) => {
      if (!enableCacheUpdates) return;

      // Update workflow detail cache
      queryClient.setQueryData<WorkflowBase>(
        WORKFLOW_QUERY_KEYS.detail(workflow.id),
        (oldData) => (oldData ? { ...oldData, ...workflow } : undefined)
      );

      // Update workflow lists cache
      queryClient.setQueriesData<{ workflows: WorkflowBase[] }>(
        { queryKey: WORKFLOW_QUERY_KEYS.lists() },
        (oldData) => {
          if (!oldData?.workflows) return oldData;
          return {
            ...oldData,
            workflows: oldData.workflows.map((w) =>
              w.id === workflow.id ? { ...w, ...workflow } : w
            ),
          };
        }
      );
    },
    [queryClient, enableCacheUpdates]
  );

  const updateWorkflowNodeInCache = useCallback(
    (workflowIdToUpdate: string, node: WorkflowNode) => {
      if (!enableCacheUpdates) return;

      queryClient.setQueryData<WorkflowBase>(
        WORKFLOW_QUERY_KEYS.detail(workflowIdToUpdate),
        (oldData) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            nodes: oldData.nodes.map((n) =>
              n.id === node.id ? { ...n, ...node } : n
            ),
          };
        }
      );
    },
    [queryClient, enableCacheUpdates]
  );

  const addWorkflowToCache = useCallback(
    (workflow: WorkflowBase) => {
      if (!enableCacheUpdates) return;

      // Set workflow detail
      queryClient.setQueryData(WORKFLOW_QUERY_KEYS.detail(workflow.id), workflow);

      // Invalidate lists to refetch
      queryClient.invalidateQueries({ queryKey: WORKFLOW_QUERY_KEYS.lists() });
    },
    [queryClient, enableCacheUpdates]
  );

  const removeWorkflowFromCache = useCallback(
    (workflowIdToRemove: string) => {
      if (!enableCacheUpdates) return;

      // Remove workflow detail
      queryClient.removeQueries({
        queryKey: WORKFLOW_QUERY_KEYS.detail(workflowIdToRemove),
      });

      // Update lists cache
      queryClient.setQueriesData<{ workflows: WorkflowBase[] }>(
        { queryKey: WORKFLOW_QUERY_KEYS.lists() },
        (oldData) => {
          if (!oldData?.workflows) return oldData;
          return {
            ...oldData,
            workflows: oldData.workflows.filter(
              (w) => w.id !== workflowIdToRemove
            ),
          };
        }
      );
    },
    [queryClient, enableCacheUpdates]
  );

  // ============================================================================
  // Node Status Helpers
  // ============================================================================

  const updateNodeStatus = useCallback(
    (wfId: string, nodeId: string, status: NodeStatus) => {
      setNodeStatuses((prev) => {
        const next = new Map(prev);
        let workflowNodes = next.get(wfId);
        if (!workflowNodes) {
          workflowNodes = new Map();
          next.set(wfId, workflowNodes);
        }
        workflowNodes.set(nodeId, status);
        return next;
      });
    },
    []
  );

  // ============================================================================
  // Review Helpers
  // ============================================================================

  const addReviewRequest = useCallback((review: HumanReviewRequest) => {
    setPendingReviews((prev) => {
      // Avoid duplicates
      if (prev.some((r) => r.id === review.id)) {
        return prev;
      }
      return [...prev, review];
    });
  }, []);

  const clearReviewRequest = useCallback((reviewId: string) => {
    setPendingReviews((prev) => prev.filter((r) => r.id !== reviewId));
  }, []);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  useEffect(() => {
    if (!enabled) return;

    const unsubscribers: (() => void)[] = [];

    // Workflow Created
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKFLOW_CREATED,
        (payload: WorkflowCreatedPayload) => {
          addWorkflowToCache(payload.workflow);

          // Initialize node statuses
          payload.workflow.nodes.forEach((node) => {
            updateNodeStatus(payload.workflow.id, node.id, node.status);
          });

          if (enableNotifications) {
            addNotification({
              type: NotificationType.INFO,
              category: NotificationCategory.WORKFLOW,
              title: 'New Workflow Created',
              message: `Workflow "${payload.workflow.name}" has been created`,
              link: `/workflows/${payload.workflow.id}`,
            });
          }

          callbacks.onWorkflowCreated?.(payload);
        }
      )
    );

    // Workflow Updated
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKFLOW_UPDATED,
        (payload: WorkflowUpdatedPayload) => {
          updateWorkflowInCache(payload.workflow);

          // Update node statuses
          payload.workflow.nodes.forEach((node) => {
            updateNodeStatus(payload.workflow.id, node.id, node.status);
          });

          callbacks.onWorkflowUpdated?.(payload);
        }
      )
    );

    // Workflow Deleted
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKFLOW_DELETED,
        (payload: WorkflowDeletedPayload) => {
          removeWorkflowFromCache(payload.workflowId);

          // Clean up local state
          setNodeStatuses((prev) => {
            const next = new Map(prev);
            next.delete(payload.workflowId);
            return next;
          });

          // Remove related reviews
          setPendingReviews((prev) =>
            prev.filter((r) => r.workflowId !== payload.workflowId)
          );

          callbacks.onWorkflowDeleted?.(payload);
        }
      )
    );

    // Workflow Status Changed
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKFLOW_STATUS_CHANGED,
        (payload: WorkflowStatusChangedPayload) => {
          updateWorkflowInCache({
            id: payload.workflowId,
            status: payload.newStatus,
            updatedAt: payload.timestamp,
          });

          if (enableNotifications) {
            if (payload.newStatus === WorkflowStatus.RUNNING) {
              addNotification({
                type: NotificationType.INFO,
                category: NotificationCategory.WORKFLOW,
                title: 'Workflow Started',
                message: 'Workflow execution has started',
                link: `/workflows/${payload.workflowId}`,
              });
            } else if (payload.newStatus === WorkflowStatus.PAUSED) {
              addNotification({
                type: NotificationType.WARNING,
                category: NotificationCategory.WORKFLOW,
                title: 'Workflow Paused',
                message: 'Workflow execution has been paused',
                link: `/workflows/${payload.workflowId}`,
              });
            }
          }

          callbacks.onWorkflowStatusChanged?.(payload);
        }
      )
    );

    // Workflow Node Updated
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKFLOW_NODE_UPDATED,
        (payload: WorkflowNodeUpdatedPayload) => {
          updateWorkflowNodeInCache(payload.workflowId, payload.node);
          updateNodeStatus(payload.workflowId, payload.node.id, payload.node.status);

          if (enableNotifications && payload.node.status === NodeStatus.FAILED) {
            addNotification({
              type: NotificationType.ERROR,
              category: NotificationCategory.WORKFLOW,
              title: 'Workflow Node Failed',
              message: `Node "${payload.node.id}" has failed`,
              link: `/workflows/${payload.workflowId}`,
            });
          }

          callbacks.onWorkflowNodeUpdated?.(payload);
        }
      )
    );

    // Workflow Review Requested
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKFLOW_REVIEW_REQUESTED,
        (payload: WorkflowReviewRequestedPayload) => {
          addReviewRequest(payload.review);

          updateWorkflowInCache({
            id: payload.workflowId,
            status: WorkflowStatus.WAITING_REVIEW,
          });

          updateNodeStatus(
            payload.workflowId,
            payload.nodeId,
            NodeStatus.WAITING_REVIEW
          );

          if (enableNotifications) {
            addNotification({
              type: NotificationType.WARNING,
              category: NotificationCategory.WORKFLOW,
              title: 'Human Review Required',
              message: payload.review.title,
              link: `/workflows/${payload.workflowId}?review=${payload.review.id}`,
            });
          }

          callbacks.onWorkflowReviewRequested?.(payload);
        }
      )
    );

    // Workflow Completed
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKFLOW_COMPLETED,
        (payload: WorkflowCompletedPayload) => {
          updateWorkflowInCache({
            id: payload.workflowId,
            status: WorkflowStatus.COMPLETED,
          });

          // Remove related reviews
          setPendingReviews((prev) =>
            prev.filter((r) => r.workflowId !== payload.workflowId)
          );

          if (enableNotifications) {
            const durationSec = Math.round(payload.duration / 1000);
            addNotification({
              type: NotificationType.SUCCESS,
              category: NotificationCategory.WORKFLOW,
              title: 'Workflow Completed',
              message: `Workflow completed in ${durationSec}s (${payload.stats.nodesExecuted} nodes executed)`,
              link: `/workflows/${payload.workflowId}`,
            });
          }

          callbacks.onWorkflowCompleted?.(payload);
        }
      )
    );

    // Workflow Failed
    unsubscribers.push(
      websocketService.on(
        WS_EVENTS.WORKFLOW_FAILED,
        (payload: WorkflowFailedPayload) => {
          updateWorkflowInCache({
            id: payload.workflowId,
            status: WorkflowStatus.FAILED,
          });

          updateNodeStatus(
            payload.workflowId,
            payload.nodeId,
            NodeStatus.FAILED
          );

          if (enableNotifications) {
            addNotification({
              type: NotificationType.ERROR,
              category: NotificationCategory.WORKFLOW,
              title: 'Workflow Failed',
              message: payload.error.message,
              link: `/workflows/${payload.workflowId}`,
            });
          }

          callbacks.onWorkflowFailed?.(payload);
        }
      )
    );

    return () => {
      unsubscribers.forEach((unsubscribe) => unsubscribe());
    };
  }, [
    enabled,
    enableNotifications,
    enableCacheUpdates,
    addWorkflowToCache,
    updateWorkflowInCache,
    updateWorkflowNodeInCache,
    removeWorkflowFromCache,
    updateNodeStatus,
    addReviewRequest,
    addNotification,
    callbacks,
  ]);

  // ============================================================================
  // Workflow Subscription Management
  // ============================================================================

  const subscribeToWorkflow = useCallback((id: string): (() => void) => {
    const channel = `workflow:${id}` as const;

    if (websocketService.isConnected()) {
      websocketService.subscribe(channel);
    }

    const unsubscribeState = websocketService.onStateChange((state) => {
      if (state === ConnectionState.CONNECTED) {
        websocketService.subscribe(channel);
      }
    });

    return () => {
      unsubscribeState();
      if (websocketService.isConnected()) {
        websocketService.unsubscribe(channel);
      }
    };
  }, []);

  const unsubscribeFromWorkflow = useCallback((id: string): void => {
    if (websocketService.isConnected()) {
      websocketService.unsubscribe(`workflow:${id}`);
    }
  }, []);

  // ============================================================================
  // Utility Functions
  // ============================================================================

  const getNodeStatus = useCallback(
    (wfId: string, nodeId: string): NodeStatus | undefined => {
      return nodeStatuses.get(wfId)?.get(nodeId);
    },
    [nodeStatuses]
  );

  return {
    pendingReviews,
    nodeStatuses,
    subscribeToWorkflow,
    unsubscribeFromWorkflow,
    clearReviewRequest,
    getNodeStatus,
  };
}

// ============================================================================
// Specialized Hooks
// ============================================================================

/**
 * Hook to subscribe to a single workflow's updates
 */
export function useWorkflowUpdate(
  workflowId: string | undefined,
  callbacks?: WorkflowUpdateCallbacks
): {
  pendingReviews: HumanReviewRequest[];
  getNodeStatus: (nodeId: string) => NodeStatus | undefined;
} {
  const { pendingReviews, nodeStatuses } = useWorkflowUpdates({
    workflowId,
    callbacks,
    enabled: !!workflowId,
  });

  const getNodeStatus = useCallback(
    (nodeId: string): NodeStatus | undefined => {
      if (!workflowId) return undefined;
      return nodeStatuses.get(workflowId)?.get(nodeId);
    },
    [workflowId, nodeStatuses]
  );

  return {
    pendingReviews: pendingReviews.filter((r) => r.workflowId === workflowId),
    getNodeStatus,
  };
}

/**
 * Hook to get all pending human review requests
 */
export function usePendingReviews(): {
  reviews: HumanReviewRequest[];
  clearReview: (reviewId: string) => void;
  count: number;
} {
  const { pendingReviews, clearReviewRequest } = useWorkflowUpdates({
    enableNotifications: false,
  });

  return {
    reviews: pendingReviews,
    clearReview: clearReviewRequest,
    count: pendingReviews.length,
  };
}

/**
 * Hook to check if any workflows need attention
 */
export function useWorkflowsNeedingAttention(): {
  hasReviewsPending: boolean;
  reviewCount: number;
} {
  const { pendingReviews } = useWorkflowUpdates({
    enableNotifications: false,
  });

  return {
    hasReviewsPending: pendingReviews.length > 0,
    reviewCount: pendingReviews.length,
  };
}

export default useWorkflowUpdates;
