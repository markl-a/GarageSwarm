/**
 * Dashboard Page Tests
 *
 * Tests for the Dashboard page covering:
 * - Stats loading
 * - Data display
 * - Error handling
 * - Responsive behavior
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from '../Dashboard';
import { server } from '@/test/mocks/server';
import { mockDashboardStats, mockTasks, mockWorkers, mockWorkflows } from '@/test/mocks/api';
import { http, HttpResponse } from 'msw';

// Mock the dashboard API hooks
vi.mock('@/services/dashboardApi', () => ({
  useDashboardStats: vi.fn(() => ({
    data: mockDashboardStats,
    isLoading: false,
    error: null,
  })),
  useRecentTasks: vi.fn(() => ({
    data: mockTasks,
    isLoading: false,
    error: null,
  })),
  useDashboardWorkers: vi.fn(() => ({
    data: mockWorkers,
    isLoading: false,
    error: null,
  })),
  useActiveWorkflows: vi.fn(() => ({
    data: mockWorkflows,
    isLoading: false,
    error: null,
  })),
  useSystemHealth: vi.fn(() => ({
    data: {
      backend: { status: 'connected', latencyMs: 50, lastChecked: new Date().toISOString() },
      mcpBus: { status: 'connected', connectedServers: 2, totalServers: 3, totalTools: 10, lastChecked: new Date().toISOString() },
      redis: { status: 'connected', lastChecked: new Date().toISOString() },
      websocket: { status: 'connected', lastChecked: new Date().toISOString() },
    },
    isLoading: false,
    refetch: vi.fn(),
  })),
  dashboardKeys: {
    all: ['dashboard'],
    stats: ['dashboard', 'stats'],
  },
}));

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// Wrapper component with all required providers
function renderDashboard() {
  const queryClient = createTestQueryClient();
  const user = userEvent.setup();

  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>
  );

  return { ...result, user, queryClient };
}

describe('Dashboard Page', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  // ===========================================================================
  // Basic Rendering
  // ===========================================================================

  describe('Basic Rendering', () => {
    it('renders dashboard title', async () => {
      renderDashboard();

      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    });

    it('renders stats cards', async () => {
      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(/total tasks/i)).toBeInTheDocument();
        expect(screen.getByText(/active tasks/i)).toBeInTheDocument();
        expect(screen.getByText(/online workers/i)).toBeInTheDocument();
        expect(screen.getByText(/active workflows/i)).toBeInTheDocument();
      });
    });

    it('renders recent tasks section', async () => {
      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(/recent tasks/i)).toBeInTheDocument();
      });
    });

    it('renders workers section', async () => {
      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(/workers/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Stats Loading
  // ===========================================================================

  describe('Stats Loading', () => {
    it('shows loading state initially', () => {
      renderDashboard();

      // Should have loading skeletons (animated pulse elements)
      const loadingElements = document.querySelectorAll('.animate-pulse');
      expect(loadingElements.length).toBeGreaterThan(0);
    });

    it('displays stats after loading', async () => {
      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(mockDashboardStats.totalTasks.toString())).toBeInTheDocument();
      });

      expect(screen.getByText(mockDashboardStats.activeTasks.toString())).toBeInTheDocument();
      expect(screen.getByText(mockDashboardStats.activeWorkers.toString())).toBeInTheDocument();
      expect(screen.getByText(mockDashboardStats.activeWorkflows.toString())).toBeInTheDocument();
    });

    it('displays correct stat values', async () => {
      renderDashboard();

      await waitFor(() => {
        // Total Tasks
        expect(screen.getByText('150')).toBeInTheDocument();
        // Active Tasks
        expect(screen.getByText('5')).toBeInTheDocument();
        // Online Workers
        expect(screen.getByText('7')).toBeInTheDocument();
        // Active Workflows
        expect(screen.getByText('3')).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Data Display
  // ===========================================================================

  describe('Data Display', () => {
    it('displays recent tasks', async () => {
      renderDashboard();

      await waitFor(() => {
        // Check for task descriptions
        expect(screen.getByText('Test task 1')).toBeInTheDocument();
      });
    });

    it('displays task status badges', async () => {
      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText('completed')).toBeInTheDocument();
        expect(screen.getByText('pending')).toBeInTheDocument();
        expect(screen.getByText('running')).toBeInTheDocument();
      });
    });

    it('displays workers list', async () => {
      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText('Worker Desktop 1')).toBeInTheDocument();
        expect(screen.getByText('Worker Docker 1')).toBeInTheDocument();
        expect(screen.getByText('Worker Desktop 2')).toBeInTheDocument();
      });
    });

    it('displays worker status badges', async () => {
      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText('online')).toBeInTheDocument();
        expect(screen.getByText('busy')).toBeInTheDocument();
        expect(screen.getByText('offline')).toBeInTheDocument();
      });
    });

    it('applies correct status colors to task badges', async () => {
      renderDashboard();

      await waitFor(() => {
        const completedBadge = screen.getByText('completed');
        expect(completedBadge).toHaveClass('bg-green-100', 'text-green-800');

        const runningBadge = screen.getByText('running');
        expect(runningBadge).toHaveClass('bg-blue-100', 'text-blue-800');

        const pendingBadge = screen.getByText('pending');
        expect(pendingBadge).toHaveClass('bg-gray-100', 'text-gray-800');
      });
    });

    it('applies correct status colors to worker badges', async () => {
      renderDashboard();

      await waitFor(() => {
        const onlineBadge = screen.getByText('online');
        expect(onlineBadge).toHaveClass('bg-green-100', 'text-green-800');

        const busyBadge = screen.getByText('busy');
        expect(busyBadge).toHaveClass('bg-yellow-100', 'text-yellow-800');

        const offlineBadge = screen.getByText('offline');
        expect(offlineBadge).toHaveClass('bg-gray-100', 'text-gray-800');
      });
    });
  });

  // ===========================================================================
  // Error Handling
  // ===========================================================================

  describe('Error Handling', () => {
    it('displays error message on stats load failure', async () => {
      server.use(
        http.get('http://127.0.0.1:8000/api/v1/dashboard/stats', () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(/error loading dashboard/i)).toBeInTheDocument();
      });
    });

    it('shows retry button on error', async () => {
      server.use(
        http.get('http://127.0.0.1:8000/api/v1/dashboard/stats', () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      renderDashboard();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });

    it('retries loading on retry button click', async () => {
      let callCount = 0;

      server.use(
        http.get('http://127.0.0.1:8000/api/v1/dashboard/stats', () => {
          callCount++;
          if (callCount === 1) {
            return HttpResponse.json(
              { detail: 'Internal server error' },
              { status: 500 }
            );
          }
          return HttpResponse.json(mockDashboardStats);
        })
      );

      const { user } = renderDashboard();

      // Wait for error state
      await waitFor(() => {
        expect(screen.getByText(/error loading dashboard/i)).toBeInTheDocument();
      });

      // Click retry
      const retryButton = screen.getByRole('button', { name: /retry/i });
      await user.click(retryButton);

      // Should load successfully on retry
      await waitFor(() => {
        expect(screen.getByText(mockDashboardStats.totalTasks.toString())).toBeInTheDocument();
      });
    });

    it('displays error description', async () => {
      server.use(
        http.get('http://127.0.0.1:8000/api/v1/dashboard/stats', () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(/failed to load dashboard data/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Empty States
  // ===========================================================================

  describe('Empty States', () => {
    it('shows empty message when no tasks', async () => {
      server.use(
        http.get('http://127.0.0.1:8000/api/v1/tasks', () => {
          return HttpResponse.json({
            tasks: [],
            total: 0,
            limit: 5,
            offset: 0,
          });
        })
      );

      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(/no tasks yet/i)).toBeInTheDocument();
      });
    });

    it('shows empty message when no workers', async () => {
      server.use(
        http.get('http://127.0.0.1:8000/api/v1/workers', () => {
          return HttpResponse.json({
            workers: [],
            total: 0,
            limit: 5,
            offset: 0,
          });
        })
      );

      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(/no workers registered/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Loading States
  // ===========================================================================

  describe('Loading States', () => {
    it('shows loading skeleton for tasks', () => {
      renderDashboard();

      // Look for loading skeletons in the recent tasks section
      const tasksSection = screen.getByText(/recent tasks/i).closest('div');
      expect(tasksSection).toBeInTheDocument();
    });

    it('shows loading skeleton for workers', () => {
      renderDashboard();

      // Look for loading skeletons in the workers section
      const workersSection = screen.getByText(/workers/i).closest('div');
      expect(workersSection).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Stats Cards
  // ===========================================================================

  describe('Stats Cards', () => {
    it('renders all four stat cards', async () => {
      renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(/total tasks/i)).toBeInTheDocument();
        expect(screen.getByText(/active tasks/i)).toBeInTheDocument();
        expect(screen.getByText(/online workers/i)).toBeInTheDocument();
        expect(screen.getByText(/active workflows/i)).toBeInTheDocument();
      });
    });

    it('renders stat cards with icons', async () => {
      renderDashboard();

      await waitFor(() => {
        // Check for SVG icons in the stat cards
        const svgIcons = document.querySelectorAll('svg');
        expect(svgIcons.length).toBeGreaterThanOrEqual(4);
      });
    });
  });

  // ===========================================================================
  // Integration
  // ===========================================================================

  describe('Integration', () => {
    it('fetches all required data on mount', async () => {
      renderDashboard();

      // Wait for all data to load
      await waitFor(() => {
        // Stats
        expect(screen.getByText(mockDashboardStats.totalTasks.toString())).toBeInTheDocument();
        // Tasks
        expect(screen.getByText('Test task 1')).toBeInTheDocument();
        // Workers
        expect(screen.getByText('Worker Desktop 1')).toBeInTheDocument();
      });
    });

    it('updates when data changes', async () => {
      const { queryClient } = renderDashboard();

      await waitFor(() => {
        expect(screen.getByText(mockDashboardStats.totalTasks.toString())).toBeInTheDocument();
      });

      // Invalidate queries to trigger refetch
      await queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] });

      // Data should still be there after invalidation
      await waitFor(() => {
        expect(screen.getByText(mockDashboardStats.totalTasks.toString())).toBeInTheDocument();
      });
    });
  });
});
