/**
 * Worker Store
 *
 * Zustand store for managing worker-related UI state.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import {
  WorkerFilters,
  WorkerSortOptions,
  ViewMode,
  ToolName,
} from '../types/worker';

// ============================================================================
// Store Interface
// ============================================================================

interface WorkerStoreState {
  // View state
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;

  // Filters
  filters: WorkerFilters;
  setFilters: (filters: Partial<WorkerFilters>) => void;
  resetFilters: () => void;

  // Sorting
  sortOptions: WorkerSortOptions;
  setSortOptions: (options: Partial<WorkerSortOptions>) => void;

  // Selection (for bulk actions)
  selectedWorkerIds: Set<string>;
  selectWorker: (workerId: string) => void;
  deselectWorker: (workerId: string) => void;
  toggleWorkerSelection: (workerId: string) => void;
  selectAllWorkers: (workerIds: string[]) => void;
  clearSelection: () => void;
  isWorkerSelected: (workerId: string) => boolean;

  // Pagination
  currentPage: number;
  pageSize: number;
  setCurrentPage: (page: number) => void;
  setPageSize: (size: number) => void;

  // Modal state
  isAddWorkerModalOpen: boolean;
  isEditWorkerModalOpen: boolean;
  isDeleteConfirmOpen: boolean;
  editingWorkerId: string | null;
  deletingWorkerId: string | null;
  openAddWorkerModal: () => void;
  closeAddWorkerModal: () => void;
  openEditWorkerModal: (workerId: string) => void;
  closeEditWorkerModal: () => void;
  openDeleteConfirm: (workerId: string) => void;
  closeDeleteConfirm: () => void;

  // Metrics time range
  metricsTimeRange: '1h' | '24h' | '7d';
  setMetricsTimeRange: (range: '1h' | '24h' | '7d') => void;
}

// ============================================================================
// Default Values
// ============================================================================

const defaultFilters: WorkerFilters = {
  status: 'all',
  tools: [],
  search: '',
};

const defaultSortOptions: WorkerSortOptions = {
  field: 'last_heartbeat',
  direction: 'desc',
};

// ============================================================================
// Store Implementation
// ============================================================================

export const useWorkerStore = create<WorkerStoreState>()(
  devtools(
    persist(
      (set, get) => ({
        // View state
        viewMode: 'table',
        setViewMode: (mode) => set({ viewMode: mode }),

        // Filters
        filters: defaultFilters,
        setFilters: (newFilters) =>
          set((state) => ({
            filters: { ...state.filters, ...newFilters },
            currentPage: 1, // Reset to first page on filter change
          })),
        resetFilters: () => set({ filters: defaultFilters, currentPage: 1 }),

        // Sorting
        sortOptions: defaultSortOptions,
        setSortOptions: (options) =>
          set((state) => ({
            sortOptions: { ...state.sortOptions, ...options },
          })),

        // Selection
        selectedWorkerIds: new Set<string>(),
        selectWorker: (workerId) =>
          set((state) => {
            const newSet = new Set(state.selectedWorkerIds);
            newSet.add(workerId);
            return { selectedWorkerIds: newSet };
          }),
        deselectWorker: (workerId) =>
          set((state) => {
            const newSet = new Set(state.selectedWorkerIds);
            newSet.delete(workerId);
            return { selectedWorkerIds: newSet };
          }),
        toggleWorkerSelection: (workerId) => {
          const { selectedWorkerIds, selectWorker, deselectWorker } = get();
          if (selectedWorkerIds.has(workerId)) {
            deselectWorker(workerId);
          } else {
            selectWorker(workerId);
          }
        },
        selectAllWorkers: (workerIds) =>
          set({ selectedWorkerIds: new Set(workerIds) }),
        clearSelection: () => set({ selectedWorkerIds: new Set() }),
        isWorkerSelected: (workerId) => get().selectedWorkerIds.has(workerId),

        // Pagination
        currentPage: 1,
        pageSize: 20,
        setCurrentPage: (page) => set({ currentPage: page }),
        setPageSize: (size) => set({ pageSize: size, currentPage: 1 }),

        // Modal state
        isAddWorkerModalOpen: false,
        isEditWorkerModalOpen: false,
        isDeleteConfirmOpen: false,
        editingWorkerId: null,
        deletingWorkerId: null,
        openAddWorkerModal: () => set({ isAddWorkerModalOpen: true }),
        closeAddWorkerModal: () => set({ isAddWorkerModalOpen: false }),
        openEditWorkerModal: (workerId) =>
          set({ isEditWorkerModalOpen: true, editingWorkerId: workerId }),
        closeEditWorkerModal: () =>
          set({ isEditWorkerModalOpen: false, editingWorkerId: null }),
        openDeleteConfirm: (workerId) =>
          set({ isDeleteConfirmOpen: true, deletingWorkerId: workerId }),
        closeDeleteConfirm: () =>
          set({ isDeleteConfirmOpen: false, deletingWorkerId: null }),

        // Metrics time range
        metricsTimeRange: '24h',
        setMetricsTimeRange: (range) => set({ metricsTimeRange: range }),
      }),
      {
        name: 'worker-store',
        // Only persist certain fields
        partialize: (state) => ({
          viewMode: state.viewMode,
          pageSize: state.pageSize,
          metricsTimeRange: state.metricsTimeRange,
        }),
      }
    ),
    { name: 'WorkerStore' }
  )
);

// ============================================================================
// Selectors
// ============================================================================

// Selector for getting filter summary text
export const useFilterSummary = () => {
  const filters = useWorkerStore((state) => state.filters);

  const parts: string[] = [];
  if (filters.status && filters.status !== 'all') {
    parts.push(`Status: ${filters.status}`);
  }
  if (filters.tools && filters.tools.length > 0) {
    parts.push(`Tools: ${filters.tools.join(', ')}`);
  }
  if (filters.search) {
    parts.push(`Search: "${filters.search}"`);
  }

  return parts.length > 0 ? parts.join(' | ') : 'All workers';
};

// Selector for getting selection count
export const useSelectionCount = () => {
  return useWorkerStore((state) => state.selectedWorkerIds.size);
};

// Selector for checking if any workers are selected
export const useHasSelection = () => {
  return useWorkerStore((state) => state.selectedWorkerIds.size > 0);
};

// Selector for getting selected worker IDs as array
export const useSelectedWorkerIds = () => {
  return useWorkerStore((state) => Array.from(state.selectedWorkerIds));
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get available tools list
 */
export const getAvailableTools = (): ToolName[] => [
  'claude_code',
  'gemini_cli',
  'ollama',
];

/**
 * Get tool display name
 */
export const getToolDisplayName = (tool: ToolName): string => {
  const names: Record<string, string> = {
    claude_code: 'Claude Code',
    gemini_cli: 'Gemini CLI',
    ollama: 'Ollama',
  };
  return names[tool] || tool;
};

/**
 * Get status color class
 */
export const getStatusColorClass = (status: string): string => {
  switch (status) {
    case 'online':
    case 'idle':
      return 'text-green-600 bg-green-100';
    case 'busy':
      return 'text-yellow-600 bg-yellow-100';
    case 'offline':
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

/**
 * Get status dot color class
 */
export const getStatusDotColor = (status: string): string => {
  switch (status) {
    case 'online':
    case 'idle':
      return 'bg-green-500';
    case 'busy':
      return 'bg-yellow-500';
    case 'offline':
    default:
      return 'bg-gray-400';
  }
};

/**
 * Format last heartbeat time
 */
export const formatLastHeartbeat = (lastHeartbeat: string | null | undefined): string => {
  if (!lastHeartbeat) return 'Never';

  const date = new Date(lastHeartbeat);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  return `${diffDay}d ago`;
};

/**
 * Format uptime from registration date
 */
export const formatUptime = (registeredAt: string): string => {
  const date = new Date(registeredAt);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDay = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHour = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

  if (diffDay > 0) {
    return `${diffDay}d ${diffHour}h`;
  }
  return `${diffHour}h`;
};
