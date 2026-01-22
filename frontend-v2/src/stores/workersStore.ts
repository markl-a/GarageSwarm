import { create } from 'zustand';
import type { Worker } from '@/types';

interface WorkersState {
  workers: Worker[];
  selectedWorker: Worker | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setWorkers: (workers: Worker[]) => void;
  addWorker: (worker: Worker) => void;
  updateWorker: (id: string, updates: Partial<Worker>) => void;
  removeWorker: (id: string) => void;
  setSelectedWorker: (worker: Worker | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useWorkersStore = create<WorkersState>((set) => ({
  workers: [],
  selectedWorker: null,
  isLoading: false,
  error: null,

  setWorkers: (workers) => set({ workers }),

  addWorker: (worker) => set((state) => ({
    workers: [...state.workers, worker]
  })),

  updateWorker: (id, updates) => set((state) => ({
    workers: state.workers.map((w) =>
      w.id === id ? { ...w, ...updates } : w
    ),
  })),

  removeWorker: (id) => set((state) => ({
    workers: state.workers.filter((w) => w.id !== id),
    selectedWorker: state.selectedWorker?.id === id ? null : state.selectedWorker,
  })),

  setSelectedWorker: (worker) => set({ selectedWorker: worker }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),
}));

export default useWorkersStore;
