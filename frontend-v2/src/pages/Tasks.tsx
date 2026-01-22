/**
 * Tasks Page
 *
 * Task list page with filters, search, pagination, and create/edit functionality.
 */

import React, { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { taskService } from '../services/taskService';
import { useTaskStore } from '../stores/taskStore';
import type { Task, TaskStatus, TaskCreate, SortConfig, StatusTab } from '../types/task';
import { TaskTable } from '../components/tasks/TaskTable';
import { TaskStatusBadge } from '../components/tasks/TaskStatusBadge';
import { TaskForm } from '../components/tasks/TaskForm';

/**
 * Status tabs configuration
 */
const STATUS_TABS: StatusTab[] = [
  { key: 'all', label: 'All Tasks' },
  { key: 'pending', label: 'Pending' },
  { key: 'running', label: 'Running' },
  { key: 'completed', label: 'Completed' },
  { key: 'failed', label: 'Failed' },
];

/**
 * Modal component for create/edit task
 */
function TaskFormModal({
  isOpen,
  onClose,
  task,
  onSubmit,
  isLoading,
}: {
  isOpen: boolean;
  onClose: () => void;
  task: Task | null;
  onSubmit: (data: TaskCreate) => void;
  isLoading: boolean;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">
              {task ? 'Edit Task' : 'Create New Task'}
            </h2>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Form */}
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
 * Pagination component
 */
function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}) {
  const totalPages = Math.ceil(total / pageSize);
  const startItem = page * pageSize + 1;
  const endItem = Math.min((page + 1) * pageSize, total);

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white border-t">
      {/* Page size selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">Show</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
        <span className="text-sm text-gray-500">entries</span>
      </div>

      {/* Page info */}
      <div className="text-sm text-gray-500">
        Showing {startItem} to {endItem} of {total} tasks
      </div>

      {/* Page navigation */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(0)}
          disabled={page === 0}
          className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="First page"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 0}
          className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Previous page"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Page numbers */}
        <div className="flex items-center gap-1 mx-2">
          {[...Array(Math.min(5, totalPages))].map((_, i) => {
            let pageNum: number;
            if (totalPages <= 5) {
              pageNum = i;
            } else if (page < 3) {
              pageNum = i;
            } else if (page > totalPages - 4) {
              pageNum = totalPages - 5 + i;
            } else {
              pageNum = page - 2 + i;
            }

            return (
              <button
                key={pageNum}
                onClick={() => onPageChange(pageNum)}
                className={`
                  w-8 h-8 text-sm font-medium rounded-md
                  ${
                    pageNum === page
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-700 hover:bg-gray-100'
                  }
                `}
              >
                {pageNum + 1}
              </button>
            );
          })}
        </div>

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages - 1}
          className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Next page"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
        <button
          onClick={() => onPageChange(totalPages - 1)}
          disabled={page >= totalPages - 1}
          className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Last page"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  );
}

/**
 * Bulk actions toolbar
 */
function BulkActionsToolbar({
  selectedCount,
  onCancel,
  onDelete,
  onClearSelection,
  isDeleting,
}: {
  selectedCount: number;
  onCancel: () => void;
  onDelete: () => void;
  onClearSelection: () => void;
  isDeleting: boolean;
}) {
  if (selectedCount === 0) return null;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-blue-50 border-b border-blue-200">
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium text-blue-700">
          {selectedCount} task{selectedCount > 1 ? 's' : ''} selected
        </span>
        <button
          onClick={onClearSelection}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Clear selection
        </button>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onCancel}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-orange-700 bg-orange-100 rounded-md hover:bg-orange-200"
        >
          Cancel Selected
        </button>
        <button
          onClick={onDelete}
          disabled={isDeleting}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200 disabled:opacity-50"
        >
          {isDeleting ? 'Deleting...' : 'Delete Selected'}
        </button>
      </div>
    </div>
  );
}

/**
 * Main Tasks page component
 */
export function Tasks() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  // Store state
  const {
    selectedTaskIds,
    isFormModalOpen,
    editingTask,
    filters,
    page,
    pageSize,
    setStatusFilter,
    setSearchFilter,
    setSortConfig,
    setPage,
    setPageSize,
    openCreateModal,
    closeFormModal,
    clearSelection,
    getQueryParams,
  } = useTaskStore();

  // Local search input state (debounced)
  const [searchInput, setSearchInput] = useState(filters.search);

  // Sync URL params with filters
  React.useEffect(() => {
    const status = searchParams.get('status');
    if (status && status !== filters.status) {
      setStatusFilter(status as TaskStatus | 'all');
    }
  }, [searchParams, filters.status, setStatusFilter]);

  // Query for fetching tasks
  const {
    data: taskData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['tasks', getQueryParams()],
    queryFn: () => taskService.list(getQueryParams()),
    staleTime: 30000, // 30 seconds
  });

  // Create task mutation
  const createTaskMutation = useMutation({
    mutationFn: (data: TaskCreate) => taskService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      closeFormModal();
    },
  });

  // Delete tasks mutation
  const deleteTasksMutation = useMutation({
    mutationFn: (taskIds: string[]) => taskService.bulkDelete(taskIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      clearSelection();
    },
  });

  // Cancel tasks mutation
  const cancelTasksMutation = useMutation({
    mutationFn: async (taskIds: string[]) => {
      await Promise.all(taskIds.map((id) => taskService.cancel(id)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      clearSelection();
    },
  });

  // Handle search with debounce
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setSearchFilter(searchInput);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput, setSearchFilter]);

  // Handle status tab change
  const handleStatusChange = useCallback(
    (status: TaskStatus | 'all') => {
      setStatusFilter(status);
      if (status === 'all') {
        searchParams.delete('status');
      } else {
        searchParams.set('status', status);
      }
      setSearchParams(searchParams);
    },
    [setStatusFilter, searchParams, setSearchParams]
  );

  // Handle sort change
  const handleSortChange = useCallback(
    (config: SortConfig) => {
      setSortConfig(config);
    },
    [setSortConfig]
  );

  // Handle form submit
  const handleFormSubmit = useCallback(
    (data: TaskCreate) => {
      createTaskMutation.mutate(data);
    },
    [createTaskMutation]
  );

  // Handle bulk delete
  const handleBulkDelete = useCallback(() => {
    if (selectedTaskIds.size > 0) {
      const confirmed = window.confirm(
        `Are you sure you want to delete ${selectedTaskIds.size} task(s)?`
      );
      if (confirmed) {
        deleteTasksMutation.mutate([...selectedTaskIds]);
      }
    }
  }, [selectedTaskIds, deleteTasksMutation]);

  // Handle bulk cancel
  const handleBulkCancel = useCallback(() => {
    if (selectedTaskIds.size > 0) {
      cancelTasksMutation.mutate([...selectedTaskIds]);
    }
  }, [selectedTaskIds, cancelTasksMutation]);

  // Calculate status counts
  const statusCounts = useMemo(() => {
    // In a real app, these would come from the API
    // For now, we'll use placeholder logic
    return STATUS_TABS.reduce((acc, tab) => {
      acc[tab.key] = tab.key === 'all' ? taskData?.total || 0 : 0;
      return acc;
    }, {} as Record<string, number>);
  }, [taskData]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tasks</h1>
          <p className="text-gray-600 mt-1">
            Manage and monitor your AI task executions
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Create Task
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow mb-6">
        {/* Status tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => handleStatusChange(tab.key)}
                className={`
                  relative px-6 py-4 text-sm font-medium border-b-2 transition-colors
                  ${
                    filters.status === tab.key
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <span className="flex items-center gap-2">
                  {tab.key !== 'all' && (
                    <TaskStatusBadge status={tab.key as TaskStatus} size="sm" showIcon={false} />
                  )}
                  {tab.key === 'all' && tab.label}
                  {statusCounts[tab.key] > 0 && (
                    <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                      {statusCounts[tab.key]}
                    </span>
                  )}
                </span>
              </button>
            ))}
          </nav>
        </div>

        {/* Search and actions bar */}
        <div className="flex items-center justify-between p-4">
          {/* Search input */}
          <div className="relative w-96">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search tasks by name or description..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {searchInput && (
              <button
                onClick={() => setSearchInput('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => refetch()}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>

        {/* Bulk actions toolbar */}
        <BulkActionsToolbar
          selectedCount={selectedTaskIds.size}
          onCancel={handleBulkCancel}
          onDelete={handleBulkDelete}
          onClearSelection={clearSelection}
          isDeleting={deleteTasksMutation.isPending}
        />
      </div>

      {/* Error state */}
      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="text-sm font-medium text-red-800">Error loading tasks</h3>
              <p className="text-sm text-red-700 mt-1">
                {error instanceof Error ? error.message : 'An unexpected error occurred'}
              </p>
            </div>
            <button
              onClick={() => refetch()}
              className="ml-auto px-3 py-1 text-sm font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Task table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <TaskTable
          tasks={taskData?.tasks || []}
          isLoading={isLoading}
          sortConfig={filters.sortConfig}
          onSort={handleSortChange}
        />

        {/* Pagination */}
        {taskData && taskData.total > 0 && (
          <Pagination
            page={page}
            pageSize={pageSize}
            total={taskData.total}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        )}
      </div>

      {/* Create/Edit Modal */}
      <TaskFormModal
        isOpen={isFormModalOpen}
        onClose={closeFormModal}
        task={editingTask}
        onSubmit={handleFormSubmit}
        isLoading={createTaskMutation.isPending}
      />
    </div>
  );
}

export default Tasks;
