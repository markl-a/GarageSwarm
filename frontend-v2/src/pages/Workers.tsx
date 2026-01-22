/**
 * Workers Page
 *
 * Main page for worker management with list/grid views,
 * filters, search, and bulk actions.
 */

import React, { useState, useMemo, useCallback } from 'react';
import { WorkerCard, WorkerCardSkeleton } from '../components/workers/WorkerCard';
import { WorkerTable } from '../components/workers/WorkerTable';
import { WorkerForm } from '../components/workers/WorkerForm';
import { ToolBadge } from '../components/workers/ToolBadge';
import {
  useWorkers,
  useDeleteWorker,
  useActivateWorker,
  useDeactivateWorker,
  useBulkWorkerAction,
  useRegisterWorker,
  useUpdateWorker,
} from '../services/workerApi';
import {
  useWorkerStore,
  useHasSelection,
  useSelectionCount,
  useSelectedWorkerIds,
  getAvailableTools,
  getStatusColorClass,
} from '../stores/workerStore';
import { Worker, WorkerFormData, WorkerSortField, WorkerStatus } from '../types/worker';

// ============================================================================
// Icons
// ============================================================================

const ViewGridIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
  </svg>
);

const ViewListIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
  </svg>
);

const PlusIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
  </svg>
);

const MagnifyingGlassIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
  </svg>
);

const FunnelIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
  </svg>
);

const XMarkIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const ChevronDownIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
  </svg>
);

const ArrowPathIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
  </svg>
);

// ============================================================================
// Subcomponents
// ============================================================================

interface StatusFilterProps {
  value: string;
  onChange: (value: WorkerStatus | 'all') => void;
}

const StatusFilter: React.FC<StatusFilterProps> = ({ value, onChange }) => {
  const statuses: Array<{ value: WorkerStatus | 'all'; label: string }> = [
    { value: 'all', label: 'All Status' },
    { value: 'online', label: 'Online' },
    { value: 'idle', label: 'Idle' },
    { value: 'busy', label: 'Busy' },
    { value: 'offline', label: 'Offline' },
  ];

  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as WorkerStatus | 'all')}
        className="appearance-none w-full pl-3 pr-10 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        {statuses.map((status) => (
          <option key={status.value} value={status.value}>
            {status.label}
          </option>
        ))}
      </select>
      <ChevronDownIcon className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
    </div>
  );
};

interface ToolsFilterProps {
  selectedTools: string[];
  onChange: (tools: string[]) => void;
}

const ToolsFilter: React.FC<ToolsFilterProps> = ({ selectedTools, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const availableTools = getAvailableTools();

  const handleToolToggle = (tool: string) => {
    if (selectedTools.includes(tool)) {
      onChange(selectedTools.filter((t) => t !== tool));
    } else {
      onChange([...selectedTools, tool]);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <FunnelIcon className="w-4 h-4 text-gray-500" />
        <span>Tools</span>
        {selectedTools.length > 0 && (
          <span className="ml-1 px-1.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
            {selectedTools.length}
          </span>
        )}
        <ChevronDownIcon className="w-4 h-4 text-gray-400" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute left-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-20">
            {availableTools.map((tool) => (
              <label
                key={tool}
                className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedTools.includes(tool)}
                  onChange={() => handleToolToggle(tool)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <ToolBadge tool={tool} size="sm" />
              </label>
            ))}
            {selectedTools.length > 0 && (
              <div className="border-t border-gray-200 mt-2 pt-2 px-4">
                <button
                  onClick={() => {
                    onChange([]);
                    setIsOpen(false);
                  }}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear all
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

interface BulkActionsBarProps {
  count: number;
  onActivate: () => void;
  onDeactivate: () => void;
  onDelete: () => void;
  onClear: () => void;
  isLoading?: boolean;
}

const BulkActionsBar: React.FC<BulkActionsBarProps> = ({
  count,
  onActivate,
  onDeactivate,
  onDelete,
  onClear,
  isLoading = false,
}) => (
  <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-blue-900">
        {count} worker{count !== 1 ? 's' : ''} selected
      </span>
      <button
        onClick={onClear}
        className="text-sm text-blue-600 hover:text-blue-800"
      >
        Clear selection
      </button>
    </div>
    <div className="flex items-center gap-2">
      <button
        onClick={onActivate}
        disabled={isLoading}
        className="px-3 py-1.5 text-sm font-medium text-green-700 bg-green-100 rounded-lg hover:bg-green-200 disabled:opacity-50 transition-colors"
      >
        Activate
      </button>
      <button
        onClick={onDeactivate}
        disabled={isLoading}
        className="px-3 py-1.5 text-sm font-medium text-yellow-700 bg-yellow-100 rounded-lg hover:bg-yellow-200 disabled:opacity-50 transition-colors"
      >
        Deactivate
      </button>
      <button
        onClick={onDelete}
        disabled={isLoading}
        className="px-3 py-1.5 text-sm font-medium text-red-700 bg-red-100 rounded-lg hover:bg-red-200 disabled:opacity-50 transition-colors"
      >
        Delete
      </button>
    </div>
  </div>
);

interface DeleteConfirmModalProps {
  isOpen: boolean;
  workerName?: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting?: boolean;
}

const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  isOpen,
  workerName,
  onConfirm,
  onCancel,
  isDeleting = false,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onCancel} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Delete Worker
          </h3>
          <p className="text-gray-600 mb-6">
            Are you sure you want to delete{' '}
            {workerName ? (
              <span className="font-medium">{workerName}</span>
            ) : (
              'this worker'
            )}
            ? This action cannot be undone.
          </p>
          <div className="flex justify-end gap-3">
            <button
              onClick={onCancel}
              disabled={isDeleting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isDeleting}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
}) => {
  if (totalPages <= 1) return null;

  const pages = useMemo(() => {
    const result: (number | 'ellipsis')[] = [];
    for (let i = 1; i <= totalPages; i++) {
      if (
        i === 1 ||
        i === totalPages ||
        (i >= currentPage - 1 && i <= currentPage + 1)
      ) {
        result.push(i);
      } else if (result[result.length - 1] !== 'ellipsis') {
        result.push('ellipsis');
      }
    }
    return result;
  }, [currentPage, totalPages]);

  return (
    <div className="flex items-center justify-center gap-1">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Previous
      </button>
      {pages.map((page, index) =>
        page === 'ellipsis' ? (
          <span key={`ellipsis-${index}`} className="px-2 text-gray-500">
            ...
          </span>
        ) : (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`px-3 py-1.5 text-sm rounded-lg ${
              page === currentPage
                ? 'bg-blue-600 text-white'
                : 'border border-gray-300 hover:bg-gray-50'
            }`}
          >
            {page}
          </button>
        )
      )}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Next
      </button>
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const Workers: React.FC = () => {
  // Store state
  const {
    viewMode,
    setViewMode,
    filters,
    setFilters,
    resetFilters,
    sortOptions,
    setSortOptions,
    currentPage,
    pageSize,
    setCurrentPage,
    clearSelection,
    isAddWorkerModalOpen,
    isEditWorkerModalOpen,
    isDeleteConfirmOpen,
    editingWorkerId,
    deletingWorkerId,
    openAddWorkerModal,
    closeAddWorkerModal,
    openEditWorkerModal,
    closeEditWorkerModal,
    openDeleteConfirm,
    closeDeleteConfirm,
  } = useWorkerStore();

  const hasSelection = useHasSelection();
  const selectionCount = useSelectionCount();
  const selectedIds = useSelectedWorkerIds();

  // Local state
  const [searchInput, setSearchInput] = useState(filters.search || '');

  // API hooks
  const {
    data: workersData,
    isLoading,
    isError,
    refetch,
  } = useWorkers(filters, pageSize, (currentPage - 1) * pageSize);

  const deleteMutation = useDeleteWorker();
  const activateMutation = useActivateWorker();
  const deactivateMutation = useDeactivateWorker();
  const bulkActionMutation = useBulkWorkerAction();
  const registerMutation = useRegisterWorker();
  const updateMutation = useUpdateWorker();

  // Computed values
  const workers = workersData?.workers ?? [];
  const totalWorkers = workersData?.total ?? 0;
  const totalPages = Math.ceil(totalWorkers / pageSize);

  // Find worker being edited/deleted
  const editingWorker = editingWorkerId
    ? workers.find((w) => w.worker_id === editingWorkerId)
    : undefined;
  const deletingWorker = deletingWorkerId
    ? workers.find((w) => w.worker_id === deletingWorkerId)
    : undefined;

  // Client-side filtering for search (API doesn't support it yet)
  const filteredWorkers = useMemo(() => {
    if (!filters.search) return workers;
    const search = filters.search.toLowerCase();
    return workers.filter(
      (w) =>
        w.machine_name.toLowerCase().includes(search) ||
        w.worker_id.toLowerCase().includes(search)
    );
  }, [workers, filters.search]);

  // Client-side sorting
  const sortedWorkers = useMemo(() => {
    const sorted = [...filteredWorkers];
    sorted.sort((a, b) => {
      const { field, direction } = sortOptions;
      let aVal: string | number | null = null;
      let bVal: string | number | null = null;

      switch (field) {
        case 'machine_name':
          aVal = a.machine_name.toLowerCase();
          bVal = b.machine_name.toLowerCase();
          break;
        case 'status':
          aVal = a.status;
          bVal = b.status;
          break;
        case 'last_heartbeat':
          aVal = a.last_heartbeat ? new Date(a.last_heartbeat).getTime() : 0;
          bVal = b.last_heartbeat ? new Date(b.last_heartbeat).getTime() : 0;
          break;
        case 'registered_at':
          aVal = new Date(a.registered_at).getTime();
          bVal = new Date(b.registered_at).getTime();
          break;
      }

      if (aVal === null || bVal === null) return 0;
      if (aVal < bVal) return direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [filteredWorkers, sortOptions]);

  // Handlers
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters({ search: searchInput });
  };

  const handleSearchClear = () => {
    setSearchInput('');
    setFilters({ search: '' });
  };

  const handleSort = (field: WorkerSortField) => {
    if (sortOptions.field === field) {
      setSortOptions({
        direction: sortOptions.direction === 'asc' ? 'desc' : 'asc',
      });
    } else {
      setSortOptions({ field, direction: 'asc' });
    }
  };

  const handleEdit = (workerId: string) => {
    openEditWorkerModal(workerId);
  };

  const handleDelete = (workerId: string) => {
    openDeleteConfirm(workerId);
  };

  const handleConfirmDelete = async () => {
    if (!deletingWorkerId) return;
    try {
      await deleteMutation.mutateAsync(deletingWorkerId);
      closeDeleteConfirm();
    } catch (error) {
      console.error('Failed to delete worker:', error);
    }
  };

  const handleActivate = async (workerId: string) => {
    try {
      await activateMutation.mutateAsync(workerId);
    } catch (error) {
      console.error('Failed to activate worker:', error);
    }
  };

  const handleDeactivate = async (workerId: string) => {
    try {
      await deactivateMutation.mutateAsync(workerId);
    } catch (error) {
      console.error('Failed to deactivate worker:', error);
    }
  };

  const handleBulkActivate = async () => {
    try {
      await bulkActionMutation.mutateAsync({ action: 'activate', workerIds: selectedIds });
      clearSelection();
    } catch (error) {
      console.error('Failed to bulk activate workers:', error);
    }
  };

  const handleBulkDeactivate = async () => {
    try {
      await bulkActionMutation.mutateAsync({ action: 'deactivate', workerIds: selectedIds });
      clearSelection();
    } catch (error) {
      console.error('Failed to bulk deactivate workers:', error);
    }
  };

  const handleBulkDelete = async () => {
    if (!confirm(`Are you sure you want to delete ${selectedIds.length} workers?`)) {
      return;
    }
    try {
      await bulkActionMutation.mutateAsync({ action: 'delete', workerIds: selectedIds });
      clearSelection();
    } catch (error) {
      console.error('Failed to bulk delete workers:', error);
    }
  };

  const handleFormSubmit = async (data: WorkerFormData) => {
    try {
      if (editingWorkerId) {
        await updateMutation.mutateAsync({ workerId: editingWorkerId, data });
        closeEditWorkerModal();
      } else {
        // For new workers, we need machine_id which is typically auto-generated
        // In a real app, this would be handled differently
        await registerMutation.mutateAsync({
          machine_id: `machine-${Date.now()}`,
          machine_name: data.machine_name,
          tools: data.tools,
        });
        closeAddWorkerModal();
      }
    } catch (error) {
      console.error('Failed to save worker:', error);
      throw error;
    }
  };

  // Active filters count
  const activeFiltersCount = [
    filters.status !== 'all' ? 1 : 0,
    (filters.tools?.length ?? 0) > 0 ? 1 : 0,
    filters.search ? 1 : 0,
  ].reduce((a, b) => a + b, 0);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Workers</h1>
            <p className="text-gray-500 mt-1">
              Manage your AI worker agents
            </p>
          </div>
          <button
            onClick={openAddWorkerModal}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
          >
            <PlusIcon className="w-5 h-5" />
            Add Worker
          </button>
        </div>

        {/* Filters bar */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[200px] max-w-md">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search workers..."
                className="w-full pl-10 pr-10 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={handleSearchClear}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              )}
            </div>
          </form>

          {/* Status filter */}
          <div className="w-36">
            <StatusFilter
              value={filters.status || 'all'}
              onChange={(value) => setFilters({ status: value })}
            />
          </div>

          {/* Tools filter */}
          <ToolsFilter
            selectedTools={filters.tools || []}
            onChange={(tools) => setFilters({ tools })}
          />

          {/* Clear filters */}
          {activeFiltersCount > 0 && (
            <button
              onClick={resetFilters}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear filters
            </button>
          )}

          {/* Refresh */}
          <button
            onClick={() => refetch()}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <ArrowPathIcon className="w-5 h-5" />
          </button>

          {/* View toggle */}
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded ${
                viewMode === 'table'
                  ? 'bg-white shadow-sm text-gray-900'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title="Table view"
            >
              <ViewListIcon className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded ${
                viewMode === 'grid'
                  ? 'bg-white shadow-sm text-gray-900'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title="Grid view"
            >
              <ViewGridIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Bulk actions bar */}
      {hasSelection && (
        <div className="mb-4">
          <BulkActionsBar
            count={selectionCount}
            onActivate={handleBulkActivate}
            onDeactivate={handleBulkDeactivate}
            onDelete={handleBulkDelete}
            onClear={clearSelection}
            isLoading={bulkActionMutation.isPending}
          />
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">
            Failed to load workers. Please try again.
          </p>
          <button
            onClick={() => refetch()}
            className="mt-2 text-sm text-red-600 hover:text-red-800"
          >
            Retry
          </button>
        </div>
      )}

      {/* Content */}
      {viewMode === 'table' ? (
        <WorkerTable
          workers={sortedWorkers}
          onSort={handleSort}
          sortField={sortOptions.field}
          sortDirection={sortOptions.direction}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onActivate={handleActivate}
          onDeactivate={handleDeactivate}
          isLoading={isLoading}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {isLoading
            ? Array.from({ length: 8 }).map((_, i) => (
                <WorkerCardSkeleton key={i} />
              ))
            : sortedWorkers.map((worker) => (
                <WorkerCard
                  key={worker.worker_id}
                  worker={worker}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onActivate={handleActivate}
                  onDeactivate={handleDeactivate}
                />
              ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && sortedWorkers.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <ViewGridIcon className="w-12 h-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-1">
            No workers found
          </h3>
          <p className="text-gray-500 mb-4">
            {activeFiltersCount > 0
              ? 'Try adjusting your filters or add a new worker.'
              : 'Get started by adding your first worker.'}
          </p>
          <button
            onClick={openAddWorkerModal}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
          >
            <PlusIcon className="w-4 h-4" />
            Add Worker
          </button>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
          />
        </div>
      )}

      {/* Summary */}
      {!isLoading && sortedWorkers.length > 0 && (
        <div className="mt-4 text-sm text-gray-500 text-center">
          Showing {sortedWorkers.length} of {totalWorkers} workers
        </div>
      )}

      {/* Add/Edit Worker Modal */}
      {(isAddWorkerModalOpen || isEditWorkerModalOpen) && (
        <WorkerForm
          worker={editingWorker}
          onSubmit={handleFormSubmit}
          onCancel={isEditWorkerModalOpen ? closeEditWorkerModal : closeAddWorkerModal}
          isSubmitting={registerMutation.isPending || updateMutation.isPending}
        />
      )}

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={isDeleteConfirmOpen}
        workerName={deletingWorker?.machine_name}
        onConfirm={handleConfirmDelete}
        onCancel={closeDeleteConfirm}
        isDeleting={deleteMutation.isPending}
      />
    </div>
  );
};

export default Workers;
