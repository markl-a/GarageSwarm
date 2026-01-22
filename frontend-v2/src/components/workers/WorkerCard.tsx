/**
 * WorkerCard Component
 *
 * A card component for displaying worker information in grid view.
 * Shows status, name, tools, metrics, and action menu.
 */

import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Worker } from '../../types/worker';
import { ToolBadgeList } from './ToolBadge';
import {
  getStatusDotColor,
  formatLastHeartbeat,
  useWorkerStore,
} from '../../stores/workerStore';

// ============================================================================
// Types
// ============================================================================

interface WorkerCardProps {
  worker: Worker;
  onEdit?: (workerId: string) => void;
  onDelete?: (workerId: string) => void;
  onActivate?: (workerId: string) => void;
  onDeactivate?: (workerId: string) => void;
}

// ============================================================================
// Icons
// ============================================================================

const EllipsisVerticalIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
  </svg>
);

const CpuChipIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
  </svg>
);

const ServerIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 17.25v-.228a4.5 4.5 0 00-.12-1.03l-2.268-9.64a3.375 3.375 0 00-3.285-2.602H7.923a3.375 3.375 0 00-3.285 2.602l-2.268 9.64a4.5 4.5 0 00-.12 1.03v.228m19.5 0a3 3 0 01-3 3H5.25a3 3 0 01-3-3m19.5 0a3 3 0 00-3-3H5.25a3 3 0 00-3 3m16.5 0h.008v.008h-.008v-.008zm-3 0h.008v.008h-.008v-.008z" />
  </svg>
);

const CircleStackIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
  </svg>
);

// ============================================================================
// Subcomponents
// ============================================================================

interface MetricBarProps {
  value: number | null | undefined;
  label: string;
  icon: React.ReactNode;
}

const MetricBar: React.FC<MetricBarProps> = ({ value, label, icon }) => {
  const percent = value ?? 0;
  const colorClass =
    percent > 90 ? 'bg-red-500' : percent > 70 ? 'bg-yellow-500' : 'bg-green-500';

  return (
    <div className="flex items-center gap-2">
      <div className="text-gray-400">{icon}</div>
      <div className="flex-1">
        <div className="flex justify-between text-xs text-gray-500 mb-0.5">
          <span>{label}</span>
          <span>{value != null ? `${value.toFixed(0)}%` : 'N/A'}</span>
        </div>
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${colorClass}`}
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const WorkerCard: React.FC<WorkerCardProps> = ({
  worker,
  onEdit,
  onDelete,
  onActivate,
  onDeactivate,
}) => {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const { toggleWorkerSelection, isWorkerSelected } = useWorkerStore();
  const isSelected = isWorkerSelected(worker.worker_id);

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [menuOpen]);

  const handleCardClick = () => {
    navigate(`/workers/${worker.worker_id}`);
  };

  const handleCheckboxClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    toggleWorkerSelection(worker.worker_id);
  };

  const handleMenuClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpen(!menuOpen);
  };

  const handleAction = (action: () => void) => {
    setMenuOpen(false);
    action();
  };

  const isOnline = worker.status === 'online' || worker.status === 'idle';

  return (
    <div
      className={`
        relative bg-white rounded-lg border shadow-sm hover:shadow-md transition-all cursor-pointer
        ${isSelected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200'}
      `}
      onClick={handleCardClick}
    >
      {/* Header */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {/* Checkbox */}
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => {}}
              onClick={handleCheckboxClick}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />

            {/* Status indicator */}
            <div className="relative">
              <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                <ServerIcon className="w-5 h-5 text-gray-600" />
              </div>
              <span
                className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white ${getStatusDotColor(worker.status)}`}
              />
            </div>

            {/* Name and ID */}
            <div>
              <h3 className="font-medium text-gray-900 truncate max-w-[150px]">
                {worker.machine_name}
              </h3>
              <p className="text-xs text-gray-500 font-mono truncate max-w-[150px]">
                {worker.worker_id.slice(0, 8)}...
              </p>
            </div>
          </div>

          {/* Menu */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={handleMenuClick}
              className="p-1 rounded-full hover:bg-gray-100 transition-colors"
            >
              <EllipsisVerticalIcon className="w-5 h-5 text-gray-500" />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-md shadow-lg border border-gray-200 py-1 z-10">
                <button
                  onClick={() => handleAction(() => navigate(`/workers/${worker.worker_id}`))}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  View Details
                </button>
                {onEdit && (
                  <button
                    onClick={() => handleAction(() => onEdit(worker.worker_id))}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Edit
                  </button>
                )}
                {isOnline && onDeactivate && (
                  <button
                    onClick={() => handleAction(() => onDeactivate(worker.worker_id))}
                    className="w-full text-left px-4 py-2 text-sm text-yellow-600 hover:bg-yellow-50"
                  >
                    Deactivate
                  </button>
                )}
                {!isOnline && onActivate && (
                  <button
                    onClick={() => handleAction(() => onActivate(worker.worker_id))}
                    className="w-full text-left px-4 py-2 text-sm text-green-600 hover:bg-green-50"
                  >
                    Activate
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={() => handleAction(() => onDelete(worker.worker_id))}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Status badge */}
        <div className="mt-3 flex items-center justify-between">
          <span
            className={`
              inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize
              ${
                worker.status === 'online' || worker.status === 'idle'
                  ? 'bg-green-100 text-green-800'
                  : worker.status === 'busy'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-gray-100 text-gray-800'
              }
            `}
          >
            {worker.status}
          </span>
          <span className="text-xs text-gray-500">
            {formatLastHeartbeat(worker.last_heartbeat)}
          </span>
        </div>
      </div>

      {/* Tools */}
      <div className="px-4 py-2 border-t border-gray-100">
        <p className="text-xs text-gray-500 mb-1.5">Tools</p>
        {worker.tools.length > 0 ? (
          <ToolBadgeList tools={worker.tools} maxVisible={3} size="sm" />
        ) : (
          <span className="text-xs text-gray-400">No tools configured</span>
        )}
      </div>

      {/* Metrics */}
      <div className="px-4 py-3 border-t border-gray-100 space-y-2">
        <MetricBar
          value={worker.cpu_percent}
          label="CPU"
          icon={<CpuChipIcon className="w-4 h-4" />}
        />
        <MetricBar
          value={worker.memory_percent}
          label="Memory"
          icon={<ServerIcon className="w-4 h-4" />}
        />
        <MetricBar
          value={worker.disk_percent}
          label="Disk"
          icon={<CircleStackIcon className="w-4 h-4" />}
        />
      </div>
    </div>
  );
};

// ============================================================================
// Skeleton Card for Loading State
// ============================================================================

export const WorkerCardSkeleton: React.FC = () => (
  <div className="bg-white rounded-lg border border-gray-200 shadow-sm animate-pulse">
    <div className="p-4 pb-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 bg-gray-200 rounded" />
          <div className="w-10 h-10 bg-gray-200 rounded-full" />
          <div>
            <div className="h-4 bg-gray-200 rounded w-24 mb-1" />
            <div className="h-3 bg-gray-200 rounded w-16" />
          </div>
        </div>
        <div className="w-6 h-6 bg-gray-200 rounded-full" />
      </div>
      <div className="mt-3 flex items-center justify-between">
        <div className="h-5 bg-gray-200 rounded-full w-16" />
        <div className="h-3 bg-gray-200 rounded w-12" />
      </div>
    </div>
    <div className="px-4 py-2 border-t border-gray-100">
      <div className="h-3 bg-gray-200 rounded w-10 mb-1.5" />
      <div className="flex gap-1">
        <div className="h-5 bg-gray-200 rounded-full w-20" />
        <div className="h-5 bg-gray-200 rounded-full w-16" />
      </div>
    </div>
    <div className="px-4 py-3 border-t border-gray-100 space-y-3">
      <div className="h-2 bg-gray-200 rounded-full" />
      <div className="h-2 bg-gray-200 rounded-full" />
      <div className="h-2 bg-gray-200 rounded-full" />
    </div>
  </div>
);

export default WorkerCard;
