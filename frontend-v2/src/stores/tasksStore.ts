import { create } from 'zustand';
import type { Task } from '@/types';

interface TasksState {
  tasks: Task[];
  selectedTask: Task | null;
  isLoading: boolean;
  error: string | null;
  filter: {
    status: Task['status'] | 'all';
    tool: Task['tool'] | 'all';
  };

  // Actions
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  removeTask: (id: string) => void;
  setSelectedTask: (task: Task | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setFilter: (filter: Partial<TasksState['filter']>) => void;
}

export const useTasksStore = create<TasksState>((set) => ({
  tasks: [],
  selectedTask: null,
  isLoading: false,
  error: null,
  filter: {
    status: 'all',
    tool: 'all',
  },

  setTasks: (tasks) => set({ tasks }),

  addTask: (task) => set((state) => ({
    tasks: [task, ...state.tasks]
  })),

  updateTask: (id, updates) => set((state) => ({
    tasks: state.tasks.map((t) =>
      t.id === id ? { ...t, ...updates } : t
    ),
  })),

  removeTask: (id) => set((state) => ({
    tasks: state.tasks.filter((t) => t.id !== id),
    selectedTask: state.selectedTask?.id === id ? null : state.selectedTask,
  })),

  setSelectedTask: (task) => set({ selectedTask: task }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  setFilter: (filter) => set((state) => ({
    filter: { ...state.filter, ...filter },
  })),
}));

export default useTasksStore;
