/**
 * WorkerGrid Component
 *
 * Displays a grid of worker cards with status indicators,
 * resource usage bars, and available tools.
 */

import React from 'react';
import { Worker, WorkerStatus, ToolName } from '../../types/worker';

// =============================================================================
// Types
// =============================================================================

export interface WorkerGridProps {
  /** Array of workers to display */
  workers: Worker[];
  /** Loading state */
  loading?: boolean;
  /** Callback when a worker card is clicked */
  onWorkerClick?: (workerId: string) => void;
  /** Maximum number of workers to show */
  maxItems?: number;
  /** Show "View All" link */
  showViewAll?: boolean;
  /** Callback for "View All" click */
  onViewAll?: () => void;
}

// =============================================================================
// Sub-components
// =============================================================================

interface StatusIndicatorProps {
  status: WorkerStatus;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status }) => {
  const statusConfig = {
    online: {
      color: 'bg-green-500',
      pulse: false,
      label: 'Online',
    },
    busy: {
      color: 'bg-blue-500',
      pulse: true,
      label: 'Busy',
    },
    idle: {
      color: 'bg-yellow-500',
      pulse: false,
      label: 'Idle',
    },
    offline: {
      color: 'bg-gray-400',
      pulse: false,
      label: 'Offline',
    },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center space-x-2">
      <span className="relative flex h-2.5 w-2.5">
        {config.pulse && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full ${config.color} opacity-75`}
          />
        )}
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${config.color}`} />
      </span>
      <span className="text-xs font-medium text-gray-600">{config.label}</span>
    </div>
  );
};

interface ResourceBarProps {
  label: string;
  value: number | null | undefined;
  color: string;
}

const ResourceBar: React.FC<ResourceBarProps> = ({ label, value, color }) => {
  const percentage = value ?? 0;
  const displayValue = value !== null && value !== undefined ? `${Math.round(percentage)}%` : 'N/A';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-500">{label}</span>
        <span className="text-gray-700 font-medium">{displayValue}</span>
      </div>
      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

interface ToolBadgeProps {
  tool: ToolName;
}

const ToolBadge: React.FC<ToolBadgeProps> = ({ tool }) => {
  // Format tool name for display
  const formatToolName = (name: string): string => {
    return name
      .replace(/_/g, ' ')
      .split(' ')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Tool-specific colors
  const getToolColor = (name: string): string => {
    if (name.includes('claude')) return 'bg-purple-100 text-purple-700 border-purple-200';
    if (name.includes('gemini')) return 'bg-blue-100 text-blue-700 border-blue-200';
    if (name.includes('ollama')) return 'bg-green-100 text-green-700 border-green-200';
    return 'bg-gray-100 text-gray-700 border-gray-200';
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getToolColor(
        tool
      )}`}
    >
      {formatToolName(tool)}
    </span>
  );
};

interface WorkerCardProps {
  worker: Worker;
  onClick?: () => void;
}

const WorkerCard: React.FC<WorkerCardProps> = ({ worker, onClick }) => {
  const isClickable = onClick !== undefined;
  const isActive = worker.status === 'online' || worker.status === 'busy';

  return (
    <div
      className={`bg-white rounded-xl border transition-all duration-200 ${
        isActive ? 'border-gray-200' : 'border-gray-100 opacity-75'
      } ${isClickable ? 'cursor-pointer hover:shadow-md hover:border-gray-300' : ''}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-gray-900 truncate">
              {worker.machine_name}
            </h4>
            <p className="text-xs text-gray-500 mt-0.5 truncate">{worker.machine_id}</p>
          </div>
          <StatusIndicator status={worker.status} />
        </div>
      </div>

      {/* Resource Usage */}
      <div className="p-4 space-y-3">
        <ResourceBar
          label="CPU"
          value={worker.cpu_percent}
          color={
            (worker.cpu_percent ?? 0) > 80
              ? 'bg-red-500'
              : (worker.cpu_percent ?? 0) > 60
              ? 'bg-yellow-500'
              : 'bg-green-500'
          }
        />
        <ResourceBar
          label="Memory"
          value={worker.memory_percent}
          color={
            (worker.memory_percent ?? 0) > 80
              ? 'bg-red-500'
              : (worker.memory_percent ?? 0) > 60
              ? 'bg-yellow-500'
              : 'bg-blue-500'
          }
        />
        {worker.disk_percent !== null && worker.disk_percent !== undefined && (
          <ResourceBar
            label="Disk"
            value={worker.disk_percent}
            color={
              worker.disk_percent > 90
                ? 'bg-red-500'
                : worker.disk_percent > 75
                ? 'bg-yellow-500'
                : 'bg-purple-500'
            }
          />
        )}
      </div>

      {/* Tools */}
      {worker.tools && worker.tools.length > 0 && (
        <div className="px-4 pb-4">
          <p className="text-xs text-gray-500 mb-2">Available Tools</p>
          <div className="flex flex-wrap gap-1">
            {worker.tools.slice(0, 3).map((tool) => (
              <ToolBadge key={tool} tool={tool} />
            ))}
            {worker.tools.length > 3 && (
              <span className="text-xs text-gray-400 self-center">
                +{worker.tools.length - 3} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Last Heartbeat */}
      {worker.last_heartbeat && (
        <div className="px-4 pb-3 pt-2 border-t border-gray-50">
          <p className="text-xs text-gray-400">
            Last seen: {new Date(worker.last_heartbeat).toLocaleTimeString()}
          </p>
        </div>
      )}
    </div>
  );
};

// Loading skeleton card
const SkeletonCard: React.FC = () => (
  <div className="bg-white rounded-xl border border-gray-100 animate-pulse">
    <div className="p-4 border-b border-gray-100">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
          <div className="h-3 bg-gray-200 rounded w-1/2" />
        </div>
        <div className="h-3 w-16 bg-gray-200 rounded" />
      </div>
    </div>
    <div className="p-4 space-y-4">
      <div className="space-y-1">
        <div className="h-2 bg-gray-200 rounded w-1/4" />
        <div className="h-1.5 bg-gray-200 rounded" />
      </div>
      <div className="space-y-1">
        <div className="h-2 bg-gray-200 rounded w-1/4" />
        <div className="h-1.5 bg-gray-200 rounded" />
      </div>
    </div>
    <div className="px-4 pb-4">
      <div className="flex gap-1">
        <div className="h-5 bg-gray-200 rounded w-16" />
        <div className="h-5 bg-gray-200 rounded w-16" />
      </div>
    </div>
  </div>
);

// =============================================================================
// Main Component
// =============================================================================

export const WorkerGrid: React.FC<WorkerGridProps> = ({
  workers,
  loading = false,
  onWorkerClick,
  maxItems = 6,
  showViewAll = true,
  onViewAll,
}) => {
  const displayWorkers = workers.slice(0, maxItems);

  // Sort workers: online/busy first, then by name
  const sortedWorkers = [...displayWorkers].sort((a, b) => {
    const statusOrder = { busy: 0, online: 1, idle: 2, offline: 3 };
    const statusDiff = statusOrder[a.status] - statusOrder[b.status];
    if (statusDiff !== 0) return statusDiff;
    return a.machine_name.localeCompare(b.machine_name);
  });

  // Count active workers
  const activeCount = workers.filter(
    (w) => w.status === 'online' || w.status === 'busy'
  ).length;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <svg
            className="w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900">Workers</h3>
          {!loading && (
            <span className="text-sm text-gray-500">
              ({activeCount} active / {workers.length} total)
            </span>
          )}
        </div>

        {showViewAll && onViewAll && (
          <button
            onClick={onViewAll}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            View All
          </button>
        )}
      </div>

      {/* Grid */}
      <div className="p-4">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        ) : workers.length === 0 ? (
          <div className="py-12 text-center">
            <svg
              className="w-12 h-12 text-gray-300 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
            <p className="text-gray-500 text-sm">No workers registered</p>
            <p className="text-gray-400 text-xs mt-1">
              Connect a worker to start processing tasks
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedWorkers.map((worker) => (
              <WorkerCard
                key={worker.worker_id}
                worker={worker}
                onClick={onWorkerClick ? () => onWorkerClick(worker.worker_id) : undefined}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer - Show count if more items exist */}
      {!loading && workers.length > maxItems && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 text-center">
          <span className="text-sm text-gray-500">
            Showing {maxItems} of {workers.length} workers
          </span>
        </div>
      )}
    </div>
  );
};

export default WorkerGrid;
