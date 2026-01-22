/**
 * Task Store
 *
 * Zustand store for task state management with React Query integration.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  Task,
  TaskStatus,
  TaskListParams,
  SortConfig,
} from '../types/task';

/**
 * Task filter state
 */
interface TaskFilters {
  status: TaskStatus | 'all';
  search: string;
  sortConfig: SortConfig;
}

/**
 * Task UI state
 */
interface TaskUIState {
  // Selected tasks for bulk operations
  selectedTaskIds: Set<string>;

  // Expanded rows in the table
  expandedRowIds: Set<string>;

  // Currently viewed task detail
  currentTaskId: string | null;

  // Create/edit modal state
  isFormModalOpen: boolean;
  editingTask: Task | null;

  // Filters
  filters: TaskFilters;

  // Pagination
  page: number;
  pageSize: number;
}

/**
 * Task store actions
 */
interface TaskActions {
  // Selection actions
  selectTask: (taskId: string) => void;
  deselectTask: (taskId: string) => void;
  toggleTaskSelection: (taskId: string) => void;
  selectAllTasks: (taskIds: string[]) => void;
  clearSelection: () => void;

  // Row expansion actions
  expandRow: (taskId: string) => void;
  collapseRow: (taskId: string) => void;
  toggleRowExpansion: (taskId: string) => void;

  // Current task actions
  setCurrentTask: (taskId: string | null) => void;

  // Modal actions
  openCreateModal: () => void;
  openEditModal: (task: Task) => void;
  closeFormModal: () => void;

  // Filter actions
  setStatusFilter: (status: TaskStatus | 'all') => void;
  setSearchFilter: (search: string) => void;
  setSortConfig: (config: SortConfig) => void;
  resetFilters: () => void;

  // Pagination actions
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;

  // Get query params from current state
  getQueryParams: () => TaskListParams;

  // Reset all state
  reset: () => void;
}

type TaskStore = TaskUIState & TaskActions;

/**
 * Default filter state
 */
const defaultFilters: TaskFilters = {
  status: 'all',
  search: '',
  sortConfig: {
    column: 'created_at',
    direction: 'desc',
  },
};

/**
 * Initial state
 */
const initialState: TaskUIState = {
  selectedTaskIds: new Set(),
  expandedRowIds: new Set(),
  currentTaskId: null,
  isFormModalOpen: false,
  editingTask: null,
  filters: defaultFilters,
  page: 0,
  pageSize: 20,
};

/**
 * Task store with devtools for debugging
 */
export const useTaskStore = create<TaskStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Selection actions
      selectTask: (taskId) =>
        set(
          (state) => ({
            selectedTaskIds: new Set([...state.selectedTaskIds, taskId]),
          }),
          false,
          'selectTask'
        ),

      deselectTask: (taskId) =>
        set(
          (state) => {
            const newSet = new Set(state.selectedTaskIds);
            newSet.delete(taskId);
            return { selectedTaskIds: newSet };
          },
          false,
          'deselectTask'
        ),

      toggleTaskSelection: (taskId) =>
        set(
          (state) => {
            const newSet = new Set(state.selectedTaskIds);
            if (newSet.has(taskId)) {
              newSet.delete(taskId);
            } else {
              newSet.add(taskId);
            }
            return { selectedTaskIds: newSet };
          },
          false,
          'toggleTaskSelection'
        ),

      selectAllTasks: (taskIds) =>
        set(
          { selectedTaskIds: new Set(taskIds) },
          false,
          'selectAllTasks'
        ),

      clearSelection: () =>
        set({ selectedTaskIds: new Set() }, false, 'clearSelection'),

      // Row expansion actions
      expandRow: (taskId) =>
        set(
          (state) => ({
            expandedRowIds: new Set([...state.expandedRowIds, taskId]),
          }),
          false,
          'expandRow'
        ),

      collapseRow: (taskId) =>
        set(
          (state) => {
            const newSet = new Set(state.expandedRowIds);
            newSet.delete(taskId);
            return { expandedRowIds: newSet };
          },
          false,
          'collapseRow'
        ),

      toggleRowExpansion: (taskId) =>
        set(
          (state) => {
            const newSet = new Set(state.expandedRowIds);
            if (newSet.has(taskId)) {
              newSet.delete(taskId);
            } else {
              newSet.add(taskId);
            }
            return { expandedRowIds: newSet };
          },
          false,
          'toggleRowExpansion'
        ),

      // Current task actions
      setCurrentTask: (taskId) =>
        set({ currentTaskId: taskId }, false, 'setCurrentTask'),

      // Modal actions
      openCreateModal: () =>
        set(
          { isFormModalOpen: true, editingTask: null },
          false,
          'openCreateModal'
        ),

      openEditModal: (task) =>
        set(
          { isFormModalOpen: true, editingTask: task },
          false,
          'openEditModal'
        ),

      closeFormModal: () =>
        set(
          { isFormModalOpen: false, editingTask: null },
          false,
          'closeFormModal'
        ),

      // Filter actions
      setStatusFilter: (status) =>
        set(
          (state) => ({
            filters: { ...state.filters, status },
            page: 0, // Reset to first page on filter change
          }),
          false,
          'setStatusFilter'
        ),

      setSearchFilter: (search) =>
        set(
          (state) => ({
            filters: { ...state.filters, search },
            page: 0,
          }),
          false,
          'setSearchFilter'
        ),

      setSortConfig: (config) =>
        set(
          (state) => ({
            filters: { ...state.filters, sortConfig: config },
          }),
          false,
          'setSortConfig'
        ),

      resetFilters: () =>
        set(
          { filters: defaultFilters, page: 0 },
          false,
          'resetFilters'
        ),

      // Pagination actions
      setPage: (page) => set({ page }, false, 'setPage'),

      setPageSize: (pageSize) =>
        set({ pageSize, page: 0 }, false, 'setPageSize'),

      // Get query params
      getQueryParams: () => {
        const state = get();
        const params: TaskListParams = {
          limit: state.pageSize,
          offset: state.page * state.pageSize,
          sort_by: state.filters.sortConfig.column as TaskListParams['sort_by'],
          sort_order: state.filters.sortConfig.direction,
        };

        if (state.filters.status !== 'all') {
          params.status = state.filters.status;
        }

        if (state.filters.search) {
          params.search = state.filters.search;
        }

        return params;
      },

      // Reset all state
      reset: () => set(initialState, false, 'reset'),
    }),
    { name: 'TaskStore' }
  )
);

// Selectors for optimized re-renders
export const selectSelectedTaskIds = (state: TaskStore) => state.selectedTaskIds;
export const selectExpandedRowIds = (state: TaskStore) => state.expandedRowIds;
export const selectCurrentTaskId = (state: TaskStore) => state.currentTaskId;
export const selectIsFormModalOpen = (state: TaskStore) => state.isFormModalOpen;
export const selectEditingTask = (state: TaskStore) => state.editingTask;
export const selectFilters = (state: TaskStore) => state.filters;
export const selectPage = (state: TaskStore) => state.page;
export const selectPageSize = (state: TaskStore) => state.pageSize;
export const selectHasSelection = (state: TaskStore) => state.selectedTaskIds.size > 0;
export const selectSelectionCount = (state: TaskStore) => state.selectedTaskIds.size;
