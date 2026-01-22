/**
 * Dashboard Page
 *
 * Main dashboard page displaying system overview with:
 * - Statistics cards for tasks, workers, and workflows
 * - Recent tasks list
 * - Worker status grid
 * - Active workflows summary
 * - System health indicators
 *
 * Uses React Query for data fetching with real-time updates.
 */

import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

// API Hooks
import {
  useDashboardStats,
  useRecentTasks,
  useDashboardWorkers,
  useActiveWorkflows,
  useSystemHealth,
  dashboardKeys,
} from '../services/dashboardApi';

// Components
import {
  StatsCard,
  TaskIcon,
  WorkerIcon,
  WorkflowIcon,
  ActivityIcon,
  CheckIcon,
  ErrorIcon,
} from '../components/dashboard/StatsCard';
import { RecentTasks } from '../components/dashboard/RecentTasks';
import { WorkerGrid } from '../components/dashboard/WorkerGrid';
import { ActiveWorkflows } from '../components/dashboard/ActiveWorkflows';
import { SystemHealth, SystemHealthCompact } from '../components/dashboard/SystemHealth';

// Types
import { StatChange } from '../types/dashboard';

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format large numbers with K/M suffix
 */
function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

/**
 * Get current time formatted for display
 */
function getCurrentTime(): string {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// =============================================================================
// Dashboard Page Component
// =============================================================================

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Data fetching with React Query
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
  } = useDashboardStats();

  const {
    data: recentTasks = [],
    isLoading: tasksLoading,
    error: tasksError,
  } = useRecentTasks(10);

  const {
    data: workers = [],
    isLoading: workersLoading,
    error: workersError,
  } = useDashboardWorkers();

  const {
    data: activeWorkflows = [],
    isLoading: workflowsLoading,
    error: workflowsError,
  } = useActiveWorkflows(5);

  const {
    data: systemHealth,
    isLoading: healthLoading,
    refetch: refetchHealth,
  } = useSystemHealth();

  // Navigation handlers
  const handleTaskClick = useCallback(
    (taskId: string) => {
      navigate(`/tasks/${taskId}`);
    },
    [navigate]
  );

  const handleWorkerClick = useCallback(
    (workerId: string) => {
      navigate(`/workers/${workerId}`);
    },
    [navigate]
  );

  const handleWorkflowClick = useCallback(
    (workflowId: string) => {
      navigate(`/workflows/${workflowId}`);
    },
    [navigate]
  );

  const handleViewAllTasks = useCallback(() => {
    navigate('/tasks');
  }, [navigate]);

  const handleViewAllWorkers = useCallback(() => {
    navigate('/workers');
  }, [navigate]);

  const handleViewAllWorkflows = useCallback(() => {
    navigate('/workflows');
  }, [navigate]);

  // Refresh all data
  const handleRefreshAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
  }, [queryClient]);

  // Mock change data (would normally come from comparing with previous period)
  const getTaskChange = (): StatChange | undefined => {
    if (!stats) return undefined;
    // This would normally be calculated from historical data
    return {
      value: 5,
      direction: 'up',
      percentage: 12.5,
    };
  };

  // Check for errors
  const hasErrors = statsError || tasksError || workersError || workflowsError;

  // Default system health for loading state
  const defaultHealth = {
    backend: { status: 'connecting' as const, latencyMs: null, lastChecked: new Date().toISOString() },
    mcpBus: { status: 'connecting' as const, connectedServers: 0, totalServers: 0, totalTools: 0, lastChecked: new Date().toISOString() },
    redis: { status: 'connecting' as const, lastChecked: new Date().toISOString() },
    websocket: { status: 'connecting' as const, lastChecked: new Date().toISOString() },
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Page Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
              <p className="mt-1 text-sm text-gray-500">
                Welcome to GarageSwarm - Multi-AI Agent Orchestration Platform
              </p>
            </div>

            <div className="flex items-center space-x-4">
              {/* System Health Compact */}
              {systemHealth && (
                <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 bg-gray-50 rounded-lg">
                  <SystemHealthCompact health={systemHealth} loading={healthLoading} />
                </div>
              )}

              {/* Real-time indicator */}
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                </span>
                <span>Live</span>
                <span className="text-gray-400">|</span>
                <span>{getCurrentTime()}</span>
              </div>

              {/* Refresh button */}
              <button
                onClick={handleRefreshAll}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                title="Refresh all data"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {hasErrors && (
        <div className="bg-red-50 border-b border-red-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center space-x-2 text-red-700">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span className="text-sm font-medium">
                Some data could not be loaded. Please try refreshing.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
          <StatsCard
            icon={<TaskIcon />}
            title="Total Tasks"
            value={stats ? formatNumber(stats.totalTasks) : '-'}
            change={getTaskChange()}
            loading={statsLoading}
            colorTheme="blue"
          />
          <StatsCard
            icon={<ActivityIcon />}
            title="Active Tasks"
            value={stats?.activeTasks ?? '-'}
            loading={statsLoading}
            colorTheme="yellow"
          />
          <StatsCard
            icon={<WorkerIcon />}
            title="Workers Online"
            value={stats ? `${stats.activeWorkers}/${stats.totalWorkers}` : '-'}
            loading={statsLoading}
            colorTheme="green"
          />
          <StatsCard
            icon={<WorkflowIcon />}
            title="Active Workflows"
            value={stats?.activeWorkflows ?? '-'}
            loading={statsLoading}
            colorTheme="purple"
          />
          <StatsCard
            icon={<CheckIcon />}
            title="Completed Today"
            value={stats?.completedTasksToday ?? '-'}
            loading={statsLoading}
            colorTheme="green"
          />
          <StatsCard
            icon={<ErrorIcon />}
            title="Failed Today"
            value={stats?.failedTasksToday ?? '-'}
            loading={statsLoading}
            colorTheme="red"
          />
        </div>

        {/* Main Grid - Two Columns */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Recent Tasks & Workers */}
          <div className="lg:col-span-2 space-y-6">
            {/* Recent Tasks */}
            <RecentTasks
              tasks={recentTasks}
              loading={tasksLoading}
              onTaskClick={handleTaskClick}
              maxItems={8}
              showViewAll
              onViewAll={handleViewAllTasks}
            />

            {/* Workers Grid */}
            <WorkerGrid
              workers={workers}
              loading={workersLoading}
              onWorkerClick={handleWorkerClick}
              maxItems={6}
              showViewAll
              onViewAll={handleViewAllWorkers}
            />
          </div>

          {/* Right Column - Workflows & System Health */}
          <div className="space-y-6">
            {/* Active Workflows */}
            <ActiveWorkflows
              workflows={activeWorkflows}
              loading={workflowsLoading}
              onWorkflowClick={handleWorkflowClick}
              maxItems={4}
              showViewAll
              onViewAll={handleViewAllWorkflows}
            />

            {/* System Health */}
            <SystemHealth
              health={systemHealth ?? defaultHealth}
              loading={healthLoading}
              detailed
              onRefresh={() => refetchHealth()}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 pt-6 border-t border-gray-200 text-center">
          <p className="text-sm text-gray-400">
            GarageSwarm v0.0.1 - Multi-AI Agent Orchestration Platform
          </p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
