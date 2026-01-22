/**
 * TaskDetail Page
 *
 * Single task detail page with full task information, logs, output, and actions.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { taskService, TaskWebSocket } from '../services/taskService';
import type { Task, TaskLog, TaskCreate } from '../types/task';
import { formatTimestamp, calculateDuration } from '../types/task';
import { TaskStatusBadge, TaskProgressIndicator } from '../components/tasks/TaskStatusBadge';
import { TaskTimeline, TaskTimelineCompact } from '../components/tasks/TaskTimeline';
import { TaskOutput } from '../components/tasks/TaskOutput';
import { TaskLogs } from '../components/tasks/TaskLogs';
import { TaskForm } from '../components/tasks/TaskForm';

/**
 * Tab configuration
 */
type TabKey = 'overview' | 'output' | 'logs';

interface Tab {
  key: TabKey;
  label: string;
  icon: React.ReactNode;
}

const TABS: Tab[] = [
  {
    key: 'overview',
    label: 'Overview',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    ),
  },
  {
    key: 'output',
    label: 'Output',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
  },
  {
    key: 'logs',
    label: 'Logs',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
      </svg>
    ),
  },
];

/**
 * Loading skeleton component
 */
function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/3 mb-4" />
      <div className="h-4 bg-gray-200 rounded w-1/2 mb-8" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="h-32 bg-gray-200 rounded" />
        <div className="h-32 bg-gray-200 rounded" />
        <div className="h-32 bg-gray-200 rounded" />
      </div>
    </div>
  );
}

/**
 * Error state component
 */
function ErrorState({
  error,
  onRetry,
}: {
  error: Error;
  onRetry: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <svg
        className="w-16 h-16 text-red-400 mb-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <h2 className="text-xl font-semibold text-gray-900 mb-2">
        Failed to load task
      </h2>
      <p className="text-gray-600 mb-4">{error.message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
      >
        Try Again
      </button>
    </div>
  );
}

/**
 * Info card component
 */
function InfoCard({
  label,
  value,
  icon,
  className = '',
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <div className="mt-1 text-lg font-medium text-gray-900">{value}</div>
        </div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
    </div>
  );
}

/**
 * Edit task modal
 */
function EditTaskModal({
  isOpen,
  onClose,
  task,
  onSubmit,
  isLoading,
}: {
  isOpen: boolean;
  onClose: () => void;
  task: Task;
  onSubmit: (data: TaskCreate) => void;
  isLoading: boolean;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">Edit Task</h2>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="p-6">
            <TaskForm
              task={task}
              onSubmit={onSubmit}
              onCancel={onClose}
              isLoading={isLoading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Main TaskDetail page component
 */
export function TaskDetail() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // State
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [logs, setLogs] = useState<TaskLog[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Fetch task data
  const {
    data: task,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => taskService.get(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      // Auto-refresh for running tasks
      const task = query.state.data;
      if (task && (task.status === 'running' || task.status === 'assigned')) {
        return 5000; // 5 seconds
      }
      return false;
    },
  });

  // Fetch logs
  const {
    data: logsData,
    refetch: refetchLogs,
  } = useQuery({
    queryKey: ['task-logs', taskId],
    queryFn: () => taskService.getLogs(taskId!),
    enabled: !!taskId,
  });

  // Update logs when data changes
  useEffect(() => {
    if (logsData) {
      setLogs(logsData);
    }
  }, [logsData]);

  // WebSocket for real-time updates
  useEffect(() => {
    if (task && (task.status === 'running' || task.status === 'assigned')) {
      setIsStreaming(true);
      const ws = new TaskWebSocket(
        task.task_id,
        (data) => {
          // Handle real-time updates
          if (data && typeof data === 'object') {
            queryClient.invalidateQueries({ queryKey: ['task', taskId] });
          }
        }
      );
      ws.connect();

      return () => {
        ws.disconnect();
        setIsStreaming(false);
      };
    } else {
      setIsStreaming(false);
    }
  }, [task?.status, task?.task_id, taskId, queryClient]);

  // Cancel task mutation
  const cancelMutation = useMutation({
    mutationFn: () => taskService.cancel(taskId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });

  // Retry task mutation
  const retryMutation = useMutation({
    mutationFn: () => taskService.retry(taskId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });

  // Delete task mutation
  const deleteMutation = useMutation({
    mutationFn: () => taskService.delete(taskId!),
    onSuccess: () => {
      navigate('/tasks');
    },
  });

  // Update task mutation
  const updateMutation = useMutation({
    mutationFn: (data: TaskCreate) => taskService.update(taskId!, {
      description: data.description,
      priority: data.priority,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      setIsEditModalOpen(false);
    },
  });

  // Handlers
  const handleCancel = useCallback(() => {
    if (window.confirm('Are you sure you want to cancel this task?')) {
      cancelMutation.mutate();
    }
  }, [cancelMutation]);

  const handleRetry = useCallback(() => {
    retryMutation.mutate();
  }, [retryMutation]);

  const handleDelete = useCallback(() => {
    if (window.confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
      deleteMutation.mutate();
    }
  }, [deleteMutation]);

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <LoadingSkeleton />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <ErrorState error={error as Error} onRetry={refetch} />
      </div>
    );
  }

  // Not found state
  if (!task) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Task not found</h2>
          <p className="text-gray-600 mb-4">The task you're looking for doesn't exist.</p>
          <Link
            to="/tasks"
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
          >
            Back to Tasks
          </Link>
        </div>
      </div>
    );
  }

  const canCancel = ['pending', 'queued', 'assigned', 'running'].includes(task.status);
  const canRetry = ['failed', 'cancelled'].includes(task.status);
  const canEdit = ['pending', 'queued'].includes(task.status);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li>
            <Link to="/tasks" className="text-blue-600 hover:text-blue-800">
              Tasks
            </Link>
          </li>
          <li className="text-gray-400">/</li>
          <li className="text-gray-600 truncate max-w-xs">
            {task.task_id.slice(0, 8)}...
          </li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-gray-900">
              Task Details
            </h1>
            <TaskStatusBadge status={task.status} size="lg" />
          </div>
          <p className="text-gray-600 line-clamp-2">{task.description}</p>
          <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
            <span className="font-mono">{task.task_id}</span>
            <span>Created {formatTimestamp(task.created_at)}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {canEdit && (
            <button
              onClick={() => setIsEditModalOpen(true)}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit
            </button>
          )}
          {canRetry && (
            <button
              onClick={handleRetry}
              disabled={retryMutation.isPending}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-blue-700 bg-blue-100 rounded-lg hover:bg-blue-200 disabled:opacity-50"
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Retry
            </button>
          )}
          {canCancel && (
            <button
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-orange-700 bg-orange-100 rounded-lg hover:bg-orange-200 disabled:opacity-50"
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Cancel
            </button>
          )}
          <button
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-red-700 bg-red-100 rounded-lg hover:bg-red-200 disabled:opacity-50"
          >
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete
          </button>
        </div>
      </div>

      {/* Progress indicator for running tasks */}
      {task.status === 'running' && (
        <div className="mb-6">
          <TaskProgressIndicator status={task.status} progress={task.progress} />
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`
                  flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-colors
                  ${
                    activeTab === tab.key
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Info cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <InfoCard
                  label="Tool"
                  value={task.tool_preference || 'Auto'}
                  icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  }
                />
                <InfoCard
                  label="Priority"
                  value={`${task.priority}/10`}
                  icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
                    </svg>
                  }
                />
                <InfoCard
                  label="Progress"
                  value={`${task.progress}%`}
                  icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  }
                />
                <InfoCard
                  label="Duration"
                  value={calculateDuration(task.started_at, task.completed_at) || '-'}
                  icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  }
                />
              </div>

              {/* Worker info */}
              {task.worker_id && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Assigned Worker</h3>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                      </svg>
                    </div>
                    <div>
                      <Link
                        to={`/workers/${task.worker_id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {task.worker_id.slice(0, 8)}...
                      </Link>
                      <p className="text-sm text-gray-500">Worker ID</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Timeline */}
              <div className="bg-gray-50 rounded-lg p-4">
                <TaskTimeline task={task} />
              </div>

              {/* Description */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-gray-800 whitespace-pre-wrap">{task.description}</p>
                </div>
              </div>
            </div>
          )}

          {/* Output Tab */}
          {activeTab === 'output' && (
            <TaskOutput task={task} />
          )}

          {/* Logs Tab */}
          {activeTab === 'logs' && (
            <TaskLogs
              taskId={task.task_id}
              logs={logs}
              isStreaming={isStreaming}
              onRefresh={refetchLogs}
            />
          )}
        </div>
      </div>

      {/* Edit Modal */}
      <EditTaskModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        task={task}
        onSubmit={(data) => updateMutation.mutate(data)}
        isLoading={updateMutation.isPending}
      />
    </div>
  );
}

export default TaskDetail;
