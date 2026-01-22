/**
 * ActiveWorkflows Component
 *
 * Displays a summary of active workflows with progress bars
 * and quick access to workflow details.
 */

import React from 'react';
import { WorkflowResponse, WorkflowStatus } from '../../types/api';

// =============================================================================
// Types
// =============================================================================

export interface ActiveWorkflowsProps {
  /** Array of workflows to display */
  workflows: WorkflowResponse[];
  /** Loading state */
  loading?: boolean;
  /** Callback when a workflow is clicked */
  onWorkflowClick?: (workflowId: string) => void;
  /** Maximum number of workflows to show */
  maxItems?: number;
  /** Show "View All" link */
  showViewAll?: boolean;
  /** Callback for "View All" click */
  onViewAll?: () => void;
}

// =============================================================================
// Sub-components
// =============================================================================

interface WorkflowStatusBadgeProps {
  status: WorkflowStatus;
}

const WorkflowStatusBadge: React.FC<WorkflowStatusBadgeProps> = ({ status }) => {
  const statusConfig: Record<
    WorkflowStatus,
    { label: string; bgColor: string; textColor: string; pulse: boolean }
  > = {
    draft: {
      label: 'Draft',
      bgColor: 'bg-gray-100',
      textColor: 'text-gray-700',
      pulse: false,
    },
    pending: {
      label: 'Pending',
      bgColor: 'bg-yellow-100',
      textColor: 'text-yellow-700',
      pulse: false,
    },
    running: {
      label: 'Running',
      bgColor: 'bg-blue-100',
      textColor: 'text-blue-700',
      pulse: true,
    },
    paused: {
      label: 'Paused',
      bgColor: 'bg-orange-100',
      textColor: 'text-orange-700',
      pulse: false,
    },
    completed: {
      label: 'Completed',
      bgColor: 'bg-green-100',
      textColor: 'text-green-700',
      pulse: false,
    },
    failed: {
      label: 'Failed',
      bgColor: 'bg-red-100',
      textColor: 'text-red-700',
      pulse: false,
    },
    cancelled: {
      label: 'Cancelled',
      bgColor: 'bg-gray-100',
      textColor: 'text-gray-700',
      pulse: false,
    },
  };

  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.textColor}`}
    >
      {config.pulse && (
        <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current animate-pulse" />
      )}
      {config.label}
    </span>
  );
};

interface ProgressBarProps {
  progress: number;
  completedNodes: number;
  totalNodes: number;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  completedNodes,
  totalNodes,
}) => {
  const percentage = Math.min(100, Math.max(0, progress));

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-xs">
        <span className="text-gray-500">
          {completedNodes} / {totalNodes} nodes
        </span>
        <span className="text-gray-700 font-medium">{percentage}%</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

interface WorkflowCardProps {
  workflow: WorkflowResponse;
  onClick?: () => void;
}

const WorkflowCard: React.FC<WorkflowCardProps> = ({ workflow, onClick }) => {
  const isClickable = onClick !== undefined;
  const isActive = workflow.status === 'running' || workflow.status === 'pending';

  // Format duration if workflow is running
  const getDuration = (): string | null => {
    if (!workflow.started_at) return null;
    const start = new Date(workflow.started_at).getTime();
    const end = workflow.completed_at
      ? new Date(workflow.completed_at).getTime()
      : Date.now();
    const durationMs = end - start;

    const seconds = Math.floor(durationMs / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  };

  const duration = getDuration();

  return (
    <div
      className={`p-4 rounded-lg border transition-all duration-200 ${
        isActive
          ? 'border-blue-200 bg-blue-50/30'
          : 'border-gray-100 bg-white hover:bg-gray-50'
      } ${isClickable ? 'cursor-pointer hover:border-gray-300' : ''}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0 mr-3">
          <h4 className="text-sm font-semibold text-gray-900 truncate">
            {workflow.name}
          </h4>
          {workflow.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
              {workflow.description}
            </p>
          )}
        </div>
        <WorkflowStatusBadge status={workflow.status} />
      </div>

      {/* Progress */}
      <ProgressBar
        progress={workflow.progress}
        completedNodes={workflow.completed_nodes}
        totalNodes={workflow.total_nodes}
      />

      {/* Footer Info */}
      <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
        <span className="flex items-center space-x-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6z"
            />
          </svg>
          <span>{workflow.workflow_type}</span>
        </span>
        {duration && (
          <span className="flex items-center space-x-1">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{duration}</span>
          </span>
        )}
      </div>
    </div>
  );
};

// Loading skeleton
const SkeletonCard: React.FC = () => (
  <div className="p-4 rounded-lg border border-gray-100 animate-pulse">
    <div className="flex items-start justify-between mb-3">
      <div className="flex-1">
        <div className="h-4 bg-gray-200 rounded w-2/3 mb-2" />
        <div className="h-3 bg-gray-200 rounded w-1/2" />
      </div>
      <div className="h-5 bg-gray-200 rounded-full w-16" />
    </div>
    <div className="space-y-2">
      <div className="h-3 bg-gray-200 rounded w-full" />
      <div className="h-2 bg-gray-200 rounded-full w-full" />
    </div>
    <div className="mt-3 flex justify-between">
      <div className="h-3 bg-gray-200 rounded w-16" />
      <div className="h-3 bg-gray-200 rounded w-12" />
    </div>
  </div>
);

// =============================================================================
// Main Component
// =============================================================================

export const ActiveWorkflows: React.FC<ActiveWorkflowsProps> = ({
  workflows,
  loading = false,
  onWorkflowClick,
  maxItems = 5,
  showViewAll = true,
  onViewAll,
}) => {
  const displayWorkflows = workflows.slice(0, maxItems);

  // Sort workflows: running first, then pending, then by progress
  const sortedWorkflows = [...displayWorkflows].sort((a, b) => {
    const statusOrder: Record<WorkflowStatus, number> = {
      running: 0,
      pending: 1,
      paused: 2,
      draft: 3,
      completed: 4,
      failed: 5,
      cancelled: 6,
    };
    const statusDiff = statusOrder[a.status] - statusOrder[b.status];
    if (statusDiff !== 0) return statusDiff;
    return b.progress - a.progress;
  });

  // Count active workflows
  const activeCount = workflows.filter(
    (w) => w.status === 'running' || w.status === 'pending'
  ).length;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <svg
            className="w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
            />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900">Active Workflows</h3>
          {!loading && (
            <span className="text-sm text-gray-500">
              ({activeCount} active)
            </span>
          )}
        </div>

        {showViewAll && onViewAll && (
          <button
            onClick={onViewAll}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            View All
          </button>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        ) : workflows.length === 0 ? (
          <div className="py-12 text-center">
            <svg
              className="w-12 h-12 text-gray-300 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
              />
            </svg>
            <p className="text-gray-500 text-sm">No active workflows</p>
            <p className="text-gray-400 text-xs mt-1">
              Create a workflow to automate multi-step tasks
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sortedWorkflows.map((workflow) => (
              <WorkflowCard
                key={workflow.workflow_id}
                workflow={workflow}
                onClick={
                  onWorkflowClick
                    ? () => onWorkflowClick(workflow.workflow_id)
                    : undefined
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer - Show count if more items exist */}
      {!loading && workflows.length > maxItems && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 text-center">
          <span className="text-sm text-gray-500">
            Showing {maxItems} of {workflows.length} workflows
          </span>
        </div>
      )}
    </div>
  );
};

export default ActiveWorkflows;
