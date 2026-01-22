/**
 * WorkerDetail Page
 *
 * Single worker detail page showing info, metrics, tools, task history,
 * and configuration options.
 */

import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  useWorker,
  useWorkerMetrics,
  useWorkerMetricsHistory,
  useWorkerTaskHistory,
  useDeleteWorker,
  useActivateWorker,
  useDeactivateWorker,
  useUpdateWorker,
} from '../services/workerApi';
import { WorkerMetrics } from '../components/workers/WorkerMetrics';
import { WorkerForm } from '../components/workers/WorkerForm';
import { ToolBadge, ToolBadgeList } from '../components/workers/ToolBadge';
import {
  getStatusDotColor,
  getStatusColorClass,
  formatLastHeartbeat,
  formatUptime,
  useWorkerStore,
} from '../stores/workerStore';
import { WorkerFormData, WorkerTaskHistoryItem } from '../types/worker';

// ============================================================================
// Icons
// ============================================================================

const ArrowLeftIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
  </svg>
);

const PencilIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
  </svg>
);

const TrashIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
  </svg>
);

const ServerIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 17.25v-.228a4.5 4.5 0 00-.12-1.03l-2.268-9.64a3.375 3.375 0 00-3.285-2.602H7.923a3.375 3.375 0 00-3.285 2.602l-2.268 9.64a4.5 4.5 0 00-.12 1.03v.228m19.5 0a3 3 0 01-3 3H5.25a3 3 0 01-3-3m19.5 0a3 3 0 00-3-3H5.25a3 3 0 00-3 3m16.5 0h.008v.008h-.008v-.008zm-3 0h.008v.008h-.008v-.008z" />
  </svg>
);

const ClockIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const SignalIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.348 14.651a3.75 3.75 0 010-5.303m5.304 0a3.75 3.75 0 010 5.303m-7.425 2.122a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.789m13.788 0c3.808 3.808 3.808 9.981 0 13.79M12 12h.008v.007H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
  </svg>
);

const CpuChipIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
  </svg>
);

const PlayIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
  </svg>
);

const PauseIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25v13.5m-7.5-13.5v13.5" />
  </svg>
);

const CheckCircleIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const XCircleIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const EllipsisHorizontalIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM12.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM18.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0z" />
  </svg>
);

// ============================================================================
// Subcomponents
// ============================================================================

interface InfoCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | React.ReactNode;
}

const InfoCard: React.FC<InfoCardProps> = ({ icon, label, value }) => (
  <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
    <div className="text-gray-400">{icon}</div>
    <div>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="font-medium text-gray-900">{value}</p>
    </div>
  </div>
);

interface TaskHistoryTableProps {
  tasks: WorkerTaskHistoryItem[];
  isLoading: boolean;
}

const TaskHistoryTable: React.FC<TaskHistoryTableProps> = ({ tasks, isLoading }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircleIcon className="w-4 h-4 text-red-500" />;
      case 'running':
        return <EllipsisHorizontalIcon className="w-4 h-4 text-blue-500 animate-pulse" />;
      default:
        return <ClockIcon className="w-4 h-4 text-gray-400" />;
    }
  };

  const formatDuration = (ms: number | null | undefined) => {
    if (ms == null) return '-';
    if (ms >= 60000) return `${(ms / 60000).toFixed(1)}m`;
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${ms}ms`;
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <div className="w-4 h-4 bg-gray-200 rounded-full" />
            <div className="flex-1">
              <div className="h-4 bg-gray-200 rounded w-2/3 mb-1" />
              <div className="h-3 bg-gray-200 rounded w-1/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No task history available</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Description
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Tool
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Duration
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Completed
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {tasks.map((task) => (
            <tr key={task.task_id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  {getStatusIcon(task.status)}
                  <span className="text-sm capitalize">{task.status}</span>
                </div>
              </td>
              <td className="px-4 py-3">
                <p className="text-sm text-gray-900 truncate max-w-xs" title={task.description}>
                  {task.description}
                </p>
              </td>
              <td className="px-4 py-3">
                {task.tool_preference ? (
                  <ToolBadge tool={task.tool_preference} size="sm" />
                ) : (
                  <span className="text-sm text-gray-400">Any</span>
                )}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {formatDuration(task.execution_time_ms)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {task.completed_at
                  ? new Date(task.completed_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

interface SystemInfoPanelProps {
  systemInfo: Record<string, string | number | undefined> | null | undefined;
}

const SystemInfoPanel: React.FC<SystemInfoPanelProps> = ({ systemInfo }) => {
  if (!systemInfo || Object.keys(systemInfo).length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <p>No system information available</p>
      </div>
    );
  }

  const formatValue = (key: string, value: string | number | undefined) => {
    if (value == null) return '-';
    if (key.includes('memory') || key.includes('disk')) {
      if (typeof value === 'number') {
        return `${value.toFixed(1)} GB`;
      }
    }
    return String(value);
  };

  const formatKey = (key: string) => {
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <dl className="grid grid-cols-2 gap-4">
      {Object.entries(systemInfo).map(([key, value]) => (
        <div key={key}>
          <dt className="text-xs text-gray-500 uppercase tracking-wide">
            {formatKey(key)}
          </dt>
          <dd className="mt-1 text-sm font-medium text-gray-900">
            {formatValue(key, value)}
          </dd>
        </div>
      ))}
    </dl>
  );
};

// ============================================================================
// Loading Skeleton
// ============================================================================

const DetailPageSkeleton: React.FC = () => (
  <div className="p-6 max-w-7xl mx-auto animate-pulse">
    {/* Back button */}
    <div className="h-4 bg-gray-200 rounded w-24 mb-6" />

    {/* Header */}
    <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-gray-200 rounded-full" />
          <div>
            <div className="h-6 bg-gray-200 rounded w-48 mb-2" />
            <div className="h-4 bg-gray-200 rounded w-32" />
          </div>
        </div>
        <div className="flex gap-2">
          <div className="w-24 h-10 bg-gray-200 rounded-lg" />
          <div className="w-24 h-10 bg-gray-200 rounded-lg" />
        </div>
      </div>
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 bg-gray-100 rounded-lg" />
        ))}
      </div>
    </div>

    {/* Content sections */}
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 h-96" />
        <div className="bg-white rounded-xl border border-gray-200 p-6 h-64" />
      </div>
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 h-48" />
        <div className="bg-white rounded-xl border border-gray-200 p-6 h-48" />
      </div>
    </div>
  </div>
);

// ============================================================================
// Main Component
// ============================================================================

export const WorkerDetail: React.FC = () => {
  const { workerId } = useParams<{ workerId: string }>();
  const navigate = useNavigate();
  const { metricsTimeRange } = useWorkerStore();

  // State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'metrics' | 'tasks' | 'config'>('metrics');

  // API hooks
  const { data: worker, isLoading: workerLoading, isError } = useWorker(workerId || '');
  const { data: metrics, isLoading: metricsLoading } = useWorkerMetrics(workerId || '');
  const { data: metricsHistory, isLoading: historyLoading } = useWorkerMetricsHistory(
    workerId || '',
    metricsTimeRange
  );
  const { data: taskHistoryData, isLoading: tasksLoading } = useWorkerTaskHistory(workerId || '');

  const deleteMutation = useDeleteWorker();
  const activateMutation = useActivateWorker();
  const deactivateMutation = useDeactivateWorker();
  const updateMutation = useUpdateWorker();

  // Handlers
  const handleDelete = async () => {
    if (!workerId) return;
    try {
      await deleteMutation.mutateAsync(workerId);
      navigate('/workers');
    } catch (error) {
      console.error('Failed to delete worker:', error);
    }
  };

  const handleActivate = async () => {
    if (!workerId) return;
    try {
      await activateMutation.mutateAsync(workerId);
    } catch (error) {
      console.error('Failed to activate worker:', error);
    }
  };

  const handleDeactivate = async () => {
    if (!workerId) return;
    try {
      await deactivateMutation.mutateAsync(workerId);
    } catch (error) {
      console.error('Failed to deactivate worker:', error);
    }
  };

  const handleFormSubmit = async (data: WorkerFormData) => {
    if (!workerId) return;
    try {
      await updateMutation.mutateAsync({ workerId, data });
      setIsEditModalOpen(false);
    } catch (error) {
      console.error('Failed to update worker:', error);
      throw error;
    }
  };

  // Loading state
  if (workerLoading) {
    return <DetailPageSkeleton />;
  }

  // Error state
  if (isError || !worker) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Worker not found</h2>
          <p className="text-gray-500 mb-4">
            The worker you're looking for doesn't exist or you don't have access to it.
          </p>
          <Link
            to="/workers"
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            Back to Workers
          </Link>
        </div>
      </div>
    );
  }

  const isOnline = worker.status === 'online' || worker.status === 'idle';

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Back button */}
      <Link
        to="/workers"
        className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeftIcon className="w-4 h-4" />
        Back to Workers
      </Link>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            {/* Worker icon */}
            <div className="relative">
              <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center">
                <ServerIcon className="w-8 h-8 text-gray-600" />
              </div>
              <span
                className={`absolute bottom-0 right-0 w-4 h-4 rounded-full border-2 border-white ${getStatusDotColor(worker.status)}`}
              />
            </div>

            {/* Name and status */}
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{worker.machine_name}</h1>
              <div className="flex items-center gap-3 mt-1">
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium capitalize ${getStatusColorClass(worker.status)}`}
                >
                  {worker.status}
                </span>
                <span className="text-sm text-gray-500 font-mono">
                  {worker.worker_id}
                </span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {isOnline ? (
              <button
                onClick={handleDeactivate}
                disabled={deactivateMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-yellow-700 bg-yellow-100 rounded-lg hover:bg-yellow-200 disabled:opacity-50 transition-colors"
              >
                <PauseIcon className="w-4 h-4" />
                Deactivate
              </button>
            ) : (
              <button
                onClick={handleActivate}
                disabled={activateMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-green-700 bg-green-100 rounded-lg hover:bg-green-200 disabled:opacity-50 transition-colors"
              >
                <PlayIcon className="w-4 h-4" />
                Activate
              </button>
            )}
            <button
              onClick={() => setIsEditModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <PencilIcon className="w-4 h-4" />
              Edit
            </button>
            <button
              onClick={() => setIsDeleteConfirmOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-300 rounded-lg hover:bg-red-50 transition-colors"
            >
              <TrashIcon className="w-4 h-4" />
              Delete
            </button>
          </div>
        </div>

        {/* Info cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <InfoCard
            icon={<SignalIcon className="w-5 h-5" />}
            label="Last Heartbeat"
            value={formatLastHeartbeat(worker.last_heartbeat)}
          />
          <InfoCard
            icon={<ClockIcon className="w-5 h-5" />}
            label="Uptime"
            value={formatUptime(worker.registered_at)}
          />
          <InfoCard
            icon={<CpuChipIcon className="w-5 h-5" />}
            label="Tools"
            value={`${worker.tools.length} configured`}
          />
          <InfoCard
            icon={<ServerIcon className="w-5 h-5" />}
            label="Registered"
            value={new Date(worker.registered_at).toLocaleDateString()}
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-8">
          {(['metrics', 'tasks', 'config'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`
                pb-4 text-sm font-medium border-b-2 transition-colors capitalize
                ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab === 'tasks' ? 'Task History' : tab === 'config' ? 'Configuration' : tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'metrics' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Metrics charts */}
          <div className="lg:col-span-2">
            <WorkerMetrics
              summary={{
                current_cpu: worker.cpu_percent ?? 0,
                current_memory: worker.memory_percent ?? 0,
                current_disk: worker.disk_percent ?? 0,
                ...(metrics || {}),
              }}
              history={metricsHistory || []}
              isLoading={metricsLoading || historyLoading}
            />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Tools */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Available Tools</h3>
              {worker.tools.length > 0 ? (
                <div className="space-y-2">
                  {worker.tools.map((tool) => (
                    <ToolBadge key={tool} tool={tool} size="md" showStatus />
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No tools configured</p>
              )}
            </div>

            {/* System info */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">System Information</h3>
              <SystemInfoPanel systemInfo={worker.system_info} />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'tasks' && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Task History</h3>
          <TaskHistoryTable
            tasks={taskHistoryData?.tasks || []}
            isLoading={tasksLoading}
          />
        </div>
      )}

      {activeTab === 'config' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Worker configuration */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Worker Configuration</h3>
            <dl className="space-y-4">
              <div>
                <dt className="text-sm text-gray-500">Machine ID</dt>
                <dd className="mt-1 text-sm font-mono text-gray-900">{worker.machine_id}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Machine Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{worker.machine_name}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Status</dt>
                <dd className="mt-1">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusColorClass(worker.status)}`}>
                    {worker.status}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Active</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {worker.is_active !== false ? 'Yes' : 'No'}
                </dd>
              </div>
            </dl>
          </div>

          {/* Tools configuration */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Tools Configuration</h3>
            {worker.tools.length > 0 ? (
              <div className="space-y-3">
                {worker.tools.map((tool) => (
                  <div
                    key={tool}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <ToolBadge tool={tool} size="md" />
                    <span className="text-sm text-green-600">Enabled</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No tools configured for this worker.</p>
            )}
            <button
              onClick={() => setIsEditModalOpen(true)}
              className="mt-4 w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
            >
              Configure Tools
            </button>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isEditModalOpen && (
        <WorkerForm
          worker={worker}
          onSubmit={handleFormSubmit}
          onCancel={() => setIsEditModalOpen(false)}
          isSubmitting={updateMutation.isPending}
        />
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteConfirmOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div
            className="fixed inset-0 bg-black bg-opacity-50"
            onClick={() => setIsDeleteConfirmOpen(false)}
          />
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Delete Worker</h3>
              <p className="text-gray-600 mb-6">
                Are you sure you want to delete{' '}
                <span className="font-medium">{worker.machine_name}</span>? This action
                cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setIsDeleteConfirmOpen(false)}
                  disabled={deleteMutation.isPending}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkerDetail;
