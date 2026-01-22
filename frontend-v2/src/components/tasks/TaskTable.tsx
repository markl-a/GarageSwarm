/**
 * TaskTable Component
 *
 * Data table for displaying tasks with sortable columns, selection, and expandable rows.
 */

import React, { useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import type { Task, SortConfig } from '../../types/task';
import { calculateDuration, formatRelativeTime } from '../../types/task';
import { TaskStatusBadge } from './TaskStatusBadge';
import { useTaskStore } from '../../stores/taskStore';

interface TaskTableProps {
  tasks: Task[];
  isLoading?: boolean;
  onSort?: (config: SortConfig) => void;
  sortConfig?: SortConfig;
}

/**
 * Column definition for the task table
 */
interface Column {
  key: string;
  label: string;
  sortable: boolean;
  width?: string;
  render: (task: Task) => React.ReactNode;
}

/**
 * Sort indicator component
 */
function SortIndicator({
  column,
  sortConfig,
}: {
  column: string;
  sortConfig?: SortConfig;
}) {
  if (!sortConfig || sortConfig.column !== column) {
    return (
      <svg className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
      </svg>
    );
  }

  return sortConfig.direction === 'asc' ? (
    <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
    </svg>
  ) : (
    <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

/**
 * Checkbox component for row selection
 */
function Checkbox({
  checked,
  indeterminate,
  onChange,
  disabled,
}: {
  checked: boolean;
  indeterminate?: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  const ref = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (ref.current) {
      ref.current.indeterminate = indeterminate || false;
    }
  }, [indeterminate]);

  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      disabled={disabled}
      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 disabled:opacity-50"
    />
  );
}

/**
 * Expanded row content component
 */
function ExpandedRowContent({ task }: { task: Task }) {
  return (
    <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Description */}
        <div className="col-span-full">
          <h4 className="text-sm font-medium text-gray-500 mb-1">Description</h4>
          <p className="text-sm text-gray-900 whitespace-pre-wrap">{task.description}</p>
        </div>

        {/* Tool Preference */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">Tool</h4>
          <p className="text-sm text-gray-900">
            {task.tool_preference || 'Auto'}
          </p>
        </div>

        {/* Priority */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">Priority</h4>
          <p className="text-sm text-gray-900">{task.priority}/10</p>
        </div>

        {/* Progress */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">Progress</h4>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${task.progress}%` }}
              />
            </div>
            <span className="text-sm text-gray-900">{task.progress}%</span>
          </div>
        </div>

        {/* Timestamps */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">Created</h4>
          <p className="text-sm text-gray-900">
            {new Date(task.created_at).toLocaleString()}
          </p>
        </div>

        {task.started_at && (
          <div>
            <h4 className="text-sm font-medium text-gray-500 mb-1">Started</h4>
            <p className="text-sm text-gray-900">
              {new Date(task.started_at).toLocaleString()}
            </p>
          </div>
        )}

        {task.completed_at && (
          <div>
            <h4 className="text-sm font-medium text-gray-500 mb-1">Completed</h4>
            <p className="text-sm text-gray-900">
              {new Date(task.completed_at).toLocaleString()}
            </p>
          </div>
        )}

        {/* Error Message */}
        {task.error && (
          <div className="col-span-full">
            <h4 className="text-sm font-medium text-red-500 mb-1">Error</h4>
            <p className="text-sm text-red-700 bg-red-50 p-2 rounded border border-red-200">
              {task.error}
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="mt-4 flex gap-2">
        <Link
          to={`/tasks/${task.task_id}`}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-100 rounded-md hover:bg-blue-200 transition-colors"
        >
          View Details
        </Link>
      </div>
    </div>
  );
}

/**
 * Loading skeleton for table rows
 */
function TableSkeleton() {
  return (
    <>
      {[...Array(5)].map((_, i) => (
        <tr key={i} className="animate-pulse">
          <td className="px-6 py-4">
            <div className="w-4 h-4 bg-gray-200 rounded" />
          </td>
          <td className="px-6 py-4">
            <div className="w-4 h-4 bg-gray-200 rounded" />
          </td>
          <td className="px-6 py-4">
            <div className="h-4 bg-gray-200 rounded w-20" />
          </td>
          <td className="px-6 py-4">
            <div className="h-4 bg-gray-200 rounded w-40" />
          </td>
          <td className="px-6 py-4">
            <div className="h-6 bg-gray-200 rounded-full w-24" />
          </td>
          <td className="px-6 py-4">
            <div className="h-4 bg-gray-200 rounded w-20" />
          </td>
          <td className="px-6 py-4">
            <div className="h-4 bg-gray-200 rounded w-24" />
          </td>
          <td className="px-6 py-4">
            <div className="h-4 bg-gray-200 rounded w-16" />
          </td>
          <td className="px-6 py-4">
            <div className="h-4 bg-gray-200 rounded w-16" />
          </td>
        </tr>
      ))}
    </>
  );
}

/**
 * Empty state component
 */
function EmptyState() {
  return (
    <tr>
      <td colSpan={9} className="px-6 py-12 text-center">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No tasks</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by creating a new task.
        </p>
      </td>
    </tr>
  );
}

/**
 * Main TaskTable component
 */
export function TaskTable({
  tasks,
  isLoading = false,
  onSort,
  sortConfig,
}: TaskTableProps) {
  const {
    selectedTaskIds,
    expandedRowIds,
    toggleTaskSelection,
    selectAllTasks,
    clearSelection,
    toggleRowExpansion,
  } = useTaskStore();

  // Column definitions
  const columns: Column[] = useMemo(
    () => [
      {
        key: 'task_id',
        label: 'ID',
        sortable: false,
        width: 'w-24',
        render: (task) => (
          <Link
            to={`/tasks/${task.task_id}`}
            className="text-blue-600 hover:text-blue-800 font-mono text-xs"
          >
            {task.task_id.slice(0, 8)}...
          </Link>
        ),
      },
      {
        key: 'description',
        label: 'Name',
        sortable: false,
        render: (task) => (
          <div className="max-w-xs truncate" title={task.description}>
            {task.description.split('\n')[0]}
          </div>
        ),
      },
      {
        key: 'status',
        label: 'Status',
        sortable: true,
        width: 'w-32',
        render: (task) => <TaskStatusBadge status={task.status} size="sm" />,
      },
      {
        key: 'tool_preference',
        label: 'Tool',
        sortable: false,
        width: 'w-28',
        render: (task) => (
          <span className="text-gray-600">{task.tool_preference || 'Auto'}</span>
        ),
      },
      {
        key: 'worker_id',
        label: 'Worker',
        sortable: false,
        width: 'w-28',
        render: (task) =>
          task.worker_id ? (
            <Link
              to={`/workers/${task.worker_id}`}
              className="text-blue-600 hover:text-blue-800 font-mono text-xs"
            >
              {task.worker_id.slice(0, 8)}...
            </Link>
          ) : (
            <span className="text-gray-400">Unassigned</span>
          ),
      },
      {
        key: 'created_at',
        label: 'Created',
        sortable: true,
        width: 'w-28',
        render: (task) => (
          <span className="text-gray-600 text-sm" title={new Date(task.created_at).toLocaleString()}>
            {formatRelativeTime(task.created_at)}
          </span>
        ),
      },
      {
        key: 'duration',
        label: 'Duration',
        sortable: false,
        width: 'w-24',
        render: (task) => {
          const duration = calculateDuration(task.started_at, task.completed_at);
          return (
            <span className="text-gray-600 text-sm">
              {duration || '-'}
            </span>
          );
        },
      },
    ],
    []
  );

  // Handle select all checkbox
  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (checked) {
        selectAllTasks(tasks.map((t) => t.task_id));
      } else {
        clearSelection();
      }
    },
    [tasks, selectAllTasks, clearSelection]
  );

  // Handle column header click for sorting
  const handleSort = useCallback(
    (column: string) => {
      if (!onSort) return;

      const newDirection =
        sortConfig?.column === column && sortConfig.direction === 'asc'
          ? 'desc'
          : 'asc';

      onSort({ column, direction: newDirection });
    },
    [onSort, sortConfig]
  );

  // Calculate selection state
  const allSelected = tasks.length > 0 && tasks.every((t) => selectedTaskIds.has(t.task_id));
  const someSelected = tasks.some((t) => selectedTaskIds.has(t.task_id)) && !allSelected;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {/* Select All Checkbox */}
            <th scope="col" className="px-6 py-3 w-12">
              <Checkbox
                checked={allSelected}
                indeterminate={someSelected}
                onChange={handleSelectAll}
                disabled={tasks.length === 0}
              />
            </th>

            {/* Expand Toggle Column */}
            <th scope="col" className="px-6 py-3 w-12">
              <span className="sr-only">Expand</span>
            </th>

            {/* Data Columns */}
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={`
                  px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider
                  ${column.width || ''}
                  ${column.sortable ? 'cursor-pointer select-none group' : ''}
                `}
                onClick={column.sortable ? () => handleSort(column.key) : undefined}
              >
                <div className="flex items-center gap-1">
                  {column.label}
                  {column.sortable && (
                    <SortIndicator column={column.key} sortConfig={sortConfig} />
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {isLoading ? (
            <TableSkeleton />
          ) : tasks.length === 0 ? (
            <EmptyState />
          ) : (
            tasks.map((task) => (
              <React.Fragment key={task.task_id}>
                {/* Main Row */}
                <tr
                  className={`
                    hover:bg-gray-50 transition-colors
                    ${selectedTaskIds.has(task.task_id) ? 'bg-blue-50' : ''}
                  `}
                >
                  {/* Selection Checkbox */}
                  <td className="px-6 py-4">
                    <Checkbox
                      checked={selectedTaskIds.has(task.task_id)}
                      onChange={() => toggleTaskSelection(task.task_id)}
                    />
                  </td>

                  {/* Expand Toggle */}
                  <td className="px-6 py-4">
                    <button
                      onClick={() => toggleRowExpansion(task.task_id)}
                      className="p-1 rounded hover:bg-gray-200 transition-colors"
                      aria-label={expandedRowIds.has(task.task_id) ? 'Collapse row' : 'Expand row'}
                    >
                      <svg
                        className={`w-4 h-4 text-gray-500 transition-transform ${
                          expandedRowIds.has(task.task_id) ? 'rotate-90' : ''
                        }`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </td>

                  {/* Data Cells */}
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={`px-6 py-4 whitespace-nowrap text-sm ${column.width || ''}`}
                    >
                      {column.render(task)}
                    </td>
                  ))}
                </tr>

                {/* Expanded Row */}
                {expandedRowIds.has(task.task_id) && (
                  <tr>
                    <td colSpan={columns.length + 2}>
                      <ExpandedRowContent task={task} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default TaskTable;
