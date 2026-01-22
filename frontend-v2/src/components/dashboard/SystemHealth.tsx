/**
 * SystemHealth Component
 *
 * Displays system health indicators for backend services,
 * MCP Bus, Redis, and WebSocket connections.
 */

import React from 'react';
import { SystemHealthStatus, ConnectionStatus } from '../../types/dashboard';

// =============================================================================
// Types
// =============================================================================

export interface SystemHealthProps {
  /** System health status data */
  health: SystemHealthStatus;
  /** Loading state */
  loading?: boolean;
  /** Show detailed view */
  detailed?: boolean;
  /** Callback to refresh health data */
  onRefresh?: () => void;
}

// =============================================================================
// Sub-components
// =============================================================================

interface StatusIconProps {
  status: ConnectionStatus;
  size?: 'sm' | 'md';
}

const StatusIcon: React.FC<StatusIconProps> = ({ status, size = 'md' }) => {
  const sizeClasses = size === 'sm' ? 'w-2.5 h-2.5' : 'w-3 h-3';

  const statusConfig: Record<ConnectionStatus, { color: string; pulse: boolean }> = {
    connected: { color: 'bg-green-500', pulse: false },
    connecting: { color: 'bg-yellow-500', pulse: true },
    disconnected: { color: 'bg-gray-400', pulse: false },
    error: { color: 'bg-red-500', pulse: true },
  };

  const config = statusConfig[status];

  return (
    <span className="relative flex">
      {config.pulse && (
        <span
          className={`animate-ping absolute inline-flex h-full w-full rounded-full ${config.color} opacity-75`}
        />
      )}
      <span className={`relative inline-flex rounded-full ${sizeClasses} ${config.color}`} />
    </span>
  );
};

interface HealthItemProps {
  label: string;
  status: ConnectionStatus;
  detail?: string;
  subDetail?: string;
  lastChecked?: string;
}

const HealthItem: React.FC<HealthItemProps> = ({
  label,
  status,
  detail,
  subDetail,
  lastChecked,
}) => {
  const statusLabels: Record<ConnectionStatus, string> = {
    connected: 'Connected',
    connecting: 'Connecting...',
    disconnected: 'Disconnected',
    error: 'Error',
  };

  const statusColors: Record<ConnectionStatus, string> = {
    connected: 'text-green-600',
    connecting: 'text-yellow-600',
    disconnected: 'text-gray-500',
    error: 'text-red-600',
  };

  // Format last checked time
  const formatLastChecked = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className="flex items-center justify-between py-3 px-4 hover:bg-gray-50 rounded-lg transition-colors">
      <div className="flex items-center space-x-3">
        <StatusIcon status={status} />
        <div>
          <p className="text-sm font-medium text-gray-900">{label}</p>
          {detail && <p className="text-xs text-gray-500">{detail}</p>}
        </div>
      </div>
      <div className="text-right">
        <p className={`text-sm font-medium ${statusColors[status]}`}>
          {statusLabels[status]}
        </p>
        {subDetail && <p className="text-xs text-gray-400">{subDetail}</p>}
        {lastChecked && (
          <p className="text-xs text-gray-400 mt-0.5">
            {formatLastChecked(lastChecked)}
          </p>
        )}
      </div>
    </div>
  );
};

// Loading skeleton
const SkeletonItem: React.FC = () => (
  <div className="flex items-center justify-between py-3 px-4 animate-pulse">
    <div className="flex items-center space-x-3">
      <div className="w-3 h-3 bg-gray-200 rounded-full" />
      <div>
        <div className="h-4 bg-gray-200 rounded w-24 mb-1" />
        <div className="h-3 bg-gray-200 rounded w-16" />
      </div>
    </div>
    <div className="text-right">
      <div className="h-4 bg-gray-200 rounded w-20 mb-1" />
      <div className="h-3 bg-gray-200 rounded w-12" />
    </div>
  </div>
);

// =============================================================================
// Main Component
// =============================================================================

export const SystemHealth: React.FC<SystemHealthProps> = ({
  health,
  loading = false,
  detailed = true,
  onRefresh,
}) => {
  // Calculate overall health status
  const getOverallStatus = (): ConnectionStatus => {
    const statuses = [
      health.backend.status,
      health.mcpBus.status,
      health.redis.status,
      health.websocket.status,
    ];

    if (statuses.includes('error')) return 'error';
    if (statuses.includes('connecting')) return 'connecting';
    if (statuses.includes('disconnected')) return 'disconnected';
    return 'connected';
  };

  const overallStatus = loading ? 'connecting' : getOverallStatus();
  const connectedCount = [
    health.backend.status,
    health.mcpBus.status,
    health.redis.status,
    health.websocket.status,
  ].filter((s) => s === 'connected').length;

  // Overall status label and color
  const overallConfig: Record<ConnectionStatus, { label: string; bgColor: string; textColor: string }> = {
    connected: { label: 'All Systems Operational', bgColor: 'bg-green-50', textColor: 'text-green-700' },
    connecting: { label: 'Checking Systems...', bgColor: 'bg-yellow-50', textColor: 'text-yellow-700' },
    disconnected: { label: 'Some Systems Offline', bgColor: 'bg-gray-50', textColor: 'text-gray-700' },
    error: { label: 'System Issues Detected', bgColor: 'bg-red-50', textColor: 'text-red-700' },
  };

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
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
            />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900">System Health</h3>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <svg
              className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Overall Status Banner */}
      <div className={`px-6 py-3 ${overallConfig[overallStatus].bgColor}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <StatusIcon status={overallStatus} size="sm" />
            <span className={`text-sm font-medium ${overallConfig[overallStatus].textColor}`}>
              {overallConfig[overallStatus].label}
            </span>
          </div>
          {!loading && (
            <span className="text-xs text-gray-500">
              {connectedCount}/4 services connected
            </span>
          )}
        </div>
      </div>

      {/* Health Items */}
      <div className="divide-y divide-gray-100">
        {loading ? (
          <>
            <SkeletonItem />
            <SkeletonItem />
            <SkeletonItem />
            <SkeletonItem />
          </>
        ) : (
          <>
            {/* Backend */}
            <HealthItem
              label="Backend API"
              status={health.backend.status}
              detail="FastAPI Server"
              subDetail={
                health.backend.latencyMs !== null
                  ? `${health.backend.latencyMs}ms latency`
                  : undefined
              }
              lastChecked={detailed ? health.backend.lastChecked : undefined}
            />

            {/* MCP Bus */}
            <HealthItem
              label="MCP Bus"
              status={health.mcpBus.status}
              detail={`${health.mcpBus.connectedServers}/${health.mcpBus.totalServers} servers`}
              subDetail={`${health.mcpBus.totalTools} tools available`}
              lastChecked={detailed ? health.mcpBus.lastChecked : undefined}
            />

            {/* Redis */}
            <HealthItem
              label="Redis"
              status={health.redis.status}
              detail="Cache & Queue"
              lastChecked={detailed ? health.redis.lastChecked : undefined}
            />

            {/* WebSocket */}
            <HealthItem
              label="WebSocket"
              status={health.websocket.status}
              detail="Real-time Updates"
              lastChecked={detailed ? health.websocket.lastChecked : undefined}
            />
          </>
        )}
      </div>

      {/* Real-time indicator */}
      {!loading && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-center space-x-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
          </span>
          <span className="text-xs text-gray-500">Real-time updates active</span>
        </div>
      )}
    </div>
  );
};

// =============================================================================
// Compact version for sidebar/header
// =============================================================================

interface SystemHealthCompactProps {
  health: SystemHealthStatus;
  loading?: boolean;
}

export const SystemHealthCompact: React.FC<SystemHealthCompactProps> = ({
  health,
  loading = false,
}) => {
  const getOverallStatus = (): ConnectionStatus => {
    if (loading) return 'connecting';
    const statuses = [
      health.backend.status,
      health.mcpBus.status,
      health.redis.status,
      health.websocket.status,
    ];
    if (statuses.includes('error')) return 'error';
    if (statuses.includes('connecting')) return 'connecting';
    if (statuses.includes('disconnected')) return 'disconnected';
    return 'connected';
  };

  const status = getOverallStatus();

  const statusConfig: Record<ConnectionStatus, { label: string; color: string }> = {
    connected: { label: 'Healthy', color: 'text-green-600' },
    connecting: { label: 'Checking...', color: 'text-yellow-600' },
    disconnected: { label: 'Degraded', color: 'text-gray-500' },
    error: { label: 'Issues', color: 'text-red-600' },
  };

  return (
    <div className="flex items-center space-x-2">
      <StatusIcon status={status} size="sm" />
      <span className={`text-xs font-medium ${statusConfig[status].color}`}>
        {statusConfig[status].label}
      </span>
    </div>
  );
};

export default SystemHealth;
