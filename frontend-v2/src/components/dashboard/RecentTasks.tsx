/**
 * RecentTasks Component
 *
 * Displays a table of recent tasks with status badges, worker info,
 * and creation time. Supports click-to-view-details.
 */

import React from 'react';
import { Task, TaskStatus, getStatusConfig, formatRelativeTime } from '../../types/task';

// =============================================================================
// Types
// =============================================================================

export interface RecentTasksProps {
  /** Array of tasks to display */
  tasks: Task[];
  /** Loading state */
  loading?: boolean;
  /** Callback when a task row is clicked */
  onTaskClick?: (taskId: string) => void;
  /** Maximum number of tasks to show */
  maxItems?: number;
  /** Show "View All" link */
  showViewAll?: boolean;
  /** Callback for "View All" click */
  onViewAll?: () => void;
}

// =============================================================================
// Sub-components
// =============================================================================

interface StatusBadgeProps {
  status: TaskStatus;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const config = getStatusConfig(status);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.color} ${config.borderColor} border`}
    >
      {config.pulseAnimation && (
        <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current animate-pulse" />
      )}
      {config.label}
    </span>
  );
};

interface TaskRowProps {
  task: Task;
  onClick?: () => void;
}

const TaskRow: React.FC<TaskRowProps> = ({ task, onClick }) => {
  // Truncate description if too long
  const truncatedDescription =
    task.description.length > 60
      ? `${task.description.substring(0, 60)}...`
      : task.description;

  return (
    <tr
      className={`hover:bg-gray-50 transition-colors ${
        onClick ? 'cursor-pointer' : ''
      }`}
      onClick={onClick}
    >
      {/* Task Description */}
      <td className="px-4 py-3">
        <div className="flex flex-col">
          <span className="text-sm font-medium text-gray-900" title={task.description}>
            {truncatedDescription}
          </span>
          {task.tool_preference && (
            <span className="text-xs text-gray-500 mt-0.5">
              Tool: {task.tool_preference}
            </span>
          )}
        </div>
      </td>

      {/* Status */}
      <td className="px-4 py-3">
        <StatusBadge status={task.status} />
      </td>

      {/* Progress (for running tasks) */}
      <td className="px-4 py-3">
        {task.status === 'running' ? (
          <div className="flex items-center space-x-2">
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden max-w-[100px]">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-300"
                style={{ width: `${task.progress}%` }}
              />
            </div>
            <span className="text-xs text-gray-500">{task.progress}%</span>
          </div>
        ) : (
          <span className="text-xs text-gray-400">-</span>
        )}
      </td>

      {/* Worker */}
      <td className="px-4 py-3">
        {task.worker_id ? (
          <span className="text-sm text-gray-600">
            {task.worker_id.slice(0, 8)}...
          </span>
        ) : (
          <span className="text-xs text-gray-400">Unassigned</span>
        )}
      </td>

      {/* Created Time */}
      <td className="px-4 py-3 text-right">
        <span className="text-sm text-gray-500" title={new Date(task.created_at).toLocaleString()}>
          {formatRelativeTime(task.created_at)}
        </span>
      </td>
    </tr>
  );
};

// Loading skeleton row
const SkeletonRow: React.FC = () => (
  <tr className="animate-pulse">
    <td className="px-4 py-3">
      <div className="h-4 bg-gray-200 rounded w-3/4" />
    </td>
    <td className="px-4 py-3">
      <div className="h-5 bg-gray-200 rounded-full w-20" />
    </td>
    <td className="px-4 py-3">
      <div className="h-2 bg-gray-200 rounded w-16" />
    </td>
    <td className="px-4 py-3">
      <div className="h-4 bg-gray-200 rounded w-16" />
    </td>
    <td className="px-4 py-3 text-right">
      <div className="h-4 bg-gray-200 rounded w-12 ml-auto" />
    </td>
  </tr>
);

// =============================================================================
// Main Component
// =============================================================================

export const RecentTasks: React.FC<RecentTasksProps> = ({
  tasks,
  loading = false,
  onTaskClick,
  maxItems = 10,
  showViewAll = true,
  onViewAll,
}) => {
  const displayTasks = tasks.slice(0, maxItems);

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
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900">Recent Tasks</h3>
          {!loading && (
            <span className="text-sm text-gray-500">
              ({tasks.length} {tasks.length === 1 ? 'task' : 'tasks'})
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

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Task
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Progress
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Worker
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {loading ? (
              // Loading skeletons
              Array.from({ length: 5 }).map((_, index) => (
                <SkeletonRow key={index} />
              ))
            ) : displayTasks.length === 0 ? (
              // Empty state
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center">
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
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                  <p className="text-gray-500 text-sm">No tasks found</p>
                  <p className="text-gray-400 text-xs mt-1">
                    Create your first task to get started
                  </p>
                </td>
              </tr>
            ) : (
              // Task rows
              displayTasks.map((task) => (
                <TaskRow
                  key={task.task_id}
                  task={task}
                  onClick={onTaskClick ? () => onTaskClick(task.task_id) : undefined}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer - Show count if more items exist */}
      {!loading && tasks.length > maxItems && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 text-center">
          <span className="text-sm text-gray-500">
            Showing {maxItems} of {tasks.length} tasks
          </span>
        </div>
      )}
    </div>
  );
};

export default RecentTasks;
