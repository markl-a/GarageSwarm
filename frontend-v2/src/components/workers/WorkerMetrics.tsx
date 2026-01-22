/**
 * WorkerMetrics Component
 *
 * Displays worker metrics including CPU, memory, disk usage charts,
 * task completion rate, and average execution time.
 */

import React, { useMemo } from 'react';
import { MetricsDataPoint, WorkerMetricsSummary } from '../../types/worker';
import { useWorkerStore } from '../../stores/workerStore';

// ============================================================================
// Types
// ============================================================================

interface WorkerMetricsProps {
  summary?: WorkerMetricsSummary;
  history?: MetricsDataPoint[];
  isLoading?: boolean;
}

interface MetricCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  colorClass?: string;
}

interface UsageGaugeProps {
  value: number;
  label: string;
  size?: 'sm' | 'md' | 'lg';
}

interface TimeSeriesChartProps {
  data: MetricsDataPoint[];
  dataKey: 'cpu_percent' | 'memory_percent' | 'disk_percent';
  label: string;
  color: string;
  height?: number;
}

// ============================================================================
// Icons
// ============================================================================

const ArrowUpIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
  </svg>
);

const ArrowDownIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3" />
  </svg>
);

// ============================================================================
// Subcomponents
// ============================================================================

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  colorClass = 'text-gray-900',
}) => (
  <div className="bg-white rounded-lg border border-gray-200 p-4">
    <p className="text-sm font-medium text-gray-500">{title}</p>
    <div className="mt-1 flex items-baseline gap-2">
      <p className={`text-2xl font-semibold ${colorClass}`}>{value}</p>
      {trend && trendValue && (
        <span
          className={`flex items-center text-sm ${
            trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-500'
          }`}
        >
          {trend === 'up' && <ArrowUpIcon className="w-3 h-3 mr-0.5" />}
          {trend === 'down' && <ArrowDownIcon className="w-3 h-3 mr-0.5" />}
          {trendValue}
        </span>
      )}
    </div>
    {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
  </div>
);

const UsageGauge: React.FC<UsageGaugeProps> = ({ value, label, size = 'md' }) => {
  const sizeConfig = {
    sm: { width: 80, strokeWidth: 6, fontSize: 'text-lg' },
    md: { width: 120, strokeWidth: 8, fontSize: 'text-2xl' },
    lg: { width: 160, strokeWidth: 10, fontSize: 'text-3xl' },
  };

  const config = sizeConfig[size];
  const radius = (config.width - config.strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;

  // Color based on value
  const getColor = (val: number) => {
    if (val > 90) return { stroke: '#ef4444', bg: '#fee2e2' }; // red
    if (val > 70) return { stroke: '#f59e0b', bg: '#fef3c7' }; // yellow
    return { stroke: '#22c55e', bg: '#dcfce7' }; // green
  };

  const colors = getColor(value);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: config.width, height: config.width }}>
        <svg className="transform -rotate-90" width={config.width} height={config.width}>
          {/* Background circle */}
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={config.strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={config.strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-500"
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`${config.fontSize} font-semibold text-gray-900`}>
            {value.toFixed(0)}%
          </span>
        </div>
      </div>
      <p className="mt-2 text-sm font-medium text-gray-600">{label}</p>
    </div>
  );
};

const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  data,
  dataKey,
  label,
  color,
  height = 120,
}) => {
  // Create SVG path from data points
  const pathData = useMemo(() => {
    if (data.length === 0) return '';

    const maxValue = 100;
    const points = data.map((point, index) => {
      const x = (index / (data.length - 1)) * 100;
      const y = 100 - (point[dataKey] / maxValue) * 100;
      return `${x},${y}`;
    });

    return `M ${points.join(' L ')}`;
  }, [data, dataKey]);

  // Area fill path
  const areaPath = useMemo(() => {
    if (data.length === 0) return '';
    return `${pathData} L 100,100 L 0,100 Z`;
  }, [pathData, data.length]);

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200"
        style={{ height }}
      >
        <p className="text-sm text-gray-500">No data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-gray-700">{label}</h4>
        <span className="text-sm text-gray-500">
          Current: {data[data.length - 1]?.[dataKey]?.toFixed(1)}%
        </span>
      </div>
      <div style={{ height }}>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
          {/* Grid lines */}
          <line x1="0" y1="25" x2="100" y2="25" stroke="#e5e7eb" strokeWidth="0.5" />
          <line x1="0" y1="50" x2="100" y2="50" stroke="#e5e7eb" strokeWidth="0.5" />
          <line x1="0" y1="75" x2="100" y2="75" stroke="#e5e7eb" strokeWidth="0.5" />

          {/* Area fill */}
          <path d={areaPath} fill={color} fillOpacity="0.1" />

          {/* Line */}
          <path
            d={pathData}
            fill="none"
            stroke={color}
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      </div>
      {/* Time labels */}
      <div className="flex justify-between mt-1">
        <span className="text-xs text-gray-400">
          {data[0]?.timestamp ? new Date(data[0].timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
        </span>
        <span className="text-xs text-gray-400">
          {data[data.length - 1]?.timestamp
            ? new Date(data[data.length - 1].timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : ''}
        </span>
      </div>
    </div>
  );
};

// ============================================================================
// Loading Skeleton
// ============================================================================

const MetricsSkeleton: React.FC = () => (
  <div className="space-y-6 animate-pulse">
    {/* Summary cards skeleton */}
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="h-4 bg-gray-200 rounded w-20 mb-2" />
          <div className="h-7 bg-gray-200 rounded w-16" />
        </div>
      ))}
    </div>

    {/* Gauges skeleton */}
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="h-5 bg-gray-200 rounded w-32 mb-4" />
      <div className="flex justify-around">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex flex-col items-center">
            <div className="w-28 h-28 bg-gray-200 rounded-full" />
            <div className="h-4 bg-gray-200 rounded w-16 mt-2" />
          </div>
        ))}
      </div>
    </div>

    {/* Charts skeleton */}
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="h-4 bg-gray-200 rounded w-24 mb-4" />
          <div className="h-28 bg-gray-100 rounded" />
        </div>
      ))}
    </div>
  </div>
);

// ============================================================================
// Main Component
// ============================================================================

export const WorkerMetrics: React.FC<WorkerMetricsProps> = ({
  summary,
  history = [],
  isLoading = false,
}) => {
  const { metricsTimeRange, setMetricsTimeRange } = useWorkerStore();

  if (isLoading) {
    return <MetricsSkeleton />;
  }

  const completionRate = summary?.task_completion_rate ?? 0;
  const avgExecutionTime = summary?.avg_execution_time_ms ?? 0;
  const formattedExecutionTime =
    avgExecutionTime >= 60000
      ? `${(avgExecutionTime / 60000).toFixed(1)}m`
      : avgExecutionTime >= 1000
      ? `${(avgExecutionTime / 1000).toFixed(1)}s`
      : `${avgExecutionTime}ms`;

  return (
    <div className="space-y-6">
      {/* Time range selector */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Resource Metrics</h3>
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          {(['1h', '24h', '7d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setMetricsTimeRange(range)}
              className={`
                px-3 py-1.5 text-sm font-medium rounded-md transition-colors
                ${
                  metricsTimeRange === range
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }
              `}
            >
              {range === '1h' ? '1 Hour' : range === '24h' ? '24 Hours' : '7 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Tasks Completed"
          value={summary?.total_tasks_completed?.toString() ?? '0'}
          subtitle="Total completed tasks"
        />
        <MetricCard
          title="Tasks Failed"
          value={summary?.total_tasks_failed?.toString() ?? '0'}
          subtitle="Total failed tasks"
          colorClass={
            (summary?.total_tasks_failed ?? 0) > 0 ? 'text-red-600' : 'text-gray-900'
          }
        />
        <MetricCard
          title="Completion Rate"
          value={`${completionRate.toFixed(1)}%`}
          subtitle="Success rate"
          colorClass={
            completionRate > 90
              ? 'text-green-600'
              : completionRate > 70
              ? 'text-yellow-600'
              : 'text-red-600'
          }
        />
        <MetricCard
          title="Avg Execution Time"
          value={formattedExecutionTime}
          subtitle="Per task average"
        />
      </div>

      {/* Current usage gauges */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h4 className="text-sm font-medium text-gray-700 mb-4">Current Resource Usage</h4>
        <div className="flex justify-around flex-wrap gap-4">
          <UsageGauge
            value={summary?.current_cpu ?? 0}
            label="CPU"
            size="md"
          />
          <UsageGauge
            value={summary?.current_memory ?? 0}
            label="Memory"
            size="md"
          />
          <UsageGauge
            value={summary?.current_disk ?? 0}
            label="Disk"
            size="md"
          />
        </div>
      </div>

      {/* Time series charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <TimeSeriesChart
          data={history}
          dataKey="cpu_percent"
          label="CPU Usage"
          color="#3b82f6"
        />
        <TimeSeriesChart
          data={history}
          dataKey="memory_percent"
          label="Memory Usage"
          color="#8b5cf6"
        />
        <TimeSeriesChart
          data={history}
          dataKey="disk_percent"
          label="Disk Usage"
          color="#f59e0b"
        />
      </div>

      {/* 24h averages */}
      {(summary?.avg_cpu_24h != null || summary?.avg_memory_24h != null) && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">24-Hour Averages</h4>
          <div className="flex gap-6">
            {summary?.avg_cpu_24h != null && (
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-blue-500 rounded-full" />
                <span className="text-sm text-gray-600">
                  CPU: {summary.avg_cpu_24h.toFixed(1)}%
                </span>
              </div>
            )}
            {summary?.avg_memory_24h != null && (
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-purple-500 rounded-full" />
                <span className="text-sm text-gray-600">
                  Memory: {summary.avg_memory_24h.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkerMetrics;
