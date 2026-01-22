/**
 * WorkerTable Component
 *
 * A table component for displaying workers with sortable columns,
 * status indicators, and row actions.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Worker, WorkerSortField, SortDirection } from '../../types/worker';
import { ToolBadgeList } from './ToolBadge';
import {
  getStatusDotColor,
  formatLastHeartbeat,
  useWorkerStore,
} from '../../stores/workerStore';

// ============================================================================
// Types
// ============================================================================

interface WorkerTableProps {
  workers: Worker[];
  onSort: (field: WorkerSortField) => void;
  sortField: WorkerSortField;
  sortDirection: SortDirection;
  onEdit?: (workerId: string) => void;
  onDelete?: (workerId: string) => void;
  onActivate?: (workerId: string) => void;
  onDeactivate?: (workerId: string) => void;
  isLoading?: boolean;
}

// ============================================================================
// Icons
// ============================================================================

const ChevronUpDownIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 15L12 18.75 15.75 15m-7.5-6L12 5.25 15.75 9" />
  </svg>
);

const ChevronUpIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
  </svg>
);

const ChevronDownIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
  </svg>
);

const EyeIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
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

// ============================================================================
// Subcomponents
// ============================================================================

interface SortableHeaderProps {
  label: string;
  field: WorkerSortField;
  currentField: WorkerSortField;
  direction: SortDirection;
  onSort: (field: WorkerSortField) => void;
}

const SortableHeader: React.FC<SortableHeaderProps> = ({
  label,
  field,
  currentField,
  direction,
  onSort,
}) => {
  const isActive = currentField === field;

  return (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-50 select-none"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        <span>{label}</span>
        {isActive ? (
          direction === 'asc' ? (
            <ChevronUpIcon className="w-4 h-4" />
          ) : (
            <ChevronDownIcon className="w-4 h-4" />
          )
        ) : (
          <ChevronUpDownIcon className="w-4 h-4 text-gray-300" />
        )}
      </div>
    </th>
  );
};

interface StatusCellProps {
  status: string;
}

const StatusCell: React.FC<StatusCellProps> = ({ status }) => (
  <div className="flex items-center gap-2">
    <span className={`w-2 h-2 rounded-full ${getStatusDotColor(status)}`} />
    <span
      className={`
        inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize
        ${
          status === 'online' || status === 'idle'
            ? 'bg-green-100 text-green-800'
            : status === 'busy'
            ? 'bg-yellow-100 text-yellow-800'
            : 'bg-gray-100 text-gray-800'
        }
      `}
    >
      {status}
    </span>
  </div>
);

interface MetricCellProps {
  cpu?: number | null;
  memory?: number | null;
}

const MetricCell: React.FC<MetricCellProps> = ({ cpu, memory }) => {
  const formatValue = (val: number | null | undefined) =>
    val != null ? `${val.toFixed(0)}%` : '-';

  return (
    <div className="text-sm">
      <div className="flex items-center gap-1">
        <span className="text-gray-500 text-xs">CPU:</span>
        <span className="font-medium">{formatValue(cpu)}</span>
      </div>
      <div className="flex items-center gap-1">
        <span className="text-gray-500 text-xs">Mem:</span>
        <span className="font-medium">{formatValue(memory)}</span>
      </div>
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const WorkerTable: React.FC<WorkerTableProps> = ({
  workers,
  onSort,
  sortField,
  sortDirection,
  onEdit,
  onDelete,
  onActivate,
  onDeactivate,
  isLoading = false,
}) => {
  const navigate = useNavigate();
  const {
    selectedWorkerIds,
    toggleWorkerSelection,
    selectAllWorkers,
    clearSelection,
  } = useWorkerStore();

  const allSelected =
    workers.length > 0 && workers.every((w) => selectedWorkerIds.has(w.worker_id));
  const someSelected =
    workers.some((w) => selectedWorkerIds.has(w.worker_id)) && !allSelected;

  const handleSelectAll = () => {
    if (allSelected) {
      clearSelection();
    } else {
      selectAllWorkers(workers.map((w) => w.worker_id));
    }
  };

  const handleRowClick = (workerId: string) => {
    navigate(`/workers/${workerId}`);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 w-10">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(input) => {
                    if (input) input.indeterminate = someSelected;
                  }}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
              </th>
              <SortableHeader
                label="Status"
                field="status"
                currentField={sortField}
                direction={sortDirection}
                onSort={onSort}
              />
              <SortableHeader
                label="Name"
                field="machine_name"
                currentField={sortField}
                direction={sortDirection}
                onSort={onSort}
              />
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tools
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Resources
              </th>
              <SortableHeader
                label="Last Heartbeat"
                field="last_heartbeat"
                currentField={sortField}
                direction={sortDirection}
                onSort={onSort}
              />
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              // Loading skeleton rows
              Array.from({ length: 5 }).map((_, index) => (
                <tr key={index} className="animate-pulse">
                  <td className="px-4 py-4">
                    <div className="w-4 h-4 bg-gray-200 rounded" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="h-5 bg-gray-200 rounded w-16" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="h-4 bg-gray-200 rounded w-32 mb-1" />
                    <div className="h-3 bg-gray-200 rounded w-20" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex gap-1">
                      <div className="h-5 bg-gray-200 rounded-full w-20" />
                      <div className="h-5 bg-gray-200 rounded-full w-16" />
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="h-4 bg-gray-200 rounded w-16 mb-1" />
                    <div className="h-4 bg-gray-200 rounded w-16" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="h-4 bg-gray-200 rounded w-12" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex justify-end gap-2">
                      <div className="w-8 h-8 bg-gray-200 rounded" />
                      <div className="w-8 h-8 bg-gray-200 rounded" />
                    </div>
                  </td>
                </tr>
              ))
            ) : workers.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center">
                  <div className="text-gray-500">
                    <p className="text-lg font-medium">No workers found</p>
                    <p className="text-sm">
                      Try adjusting your filters or add a new worker.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              workers.map((worker) => {
                const isSelected = selectedWorkerIds.has(worker.worker_id);
                const isOnline =
                  worker.status === 'online' || worker.status === 'idle';

                return (
                  <tr
                    key={worker.worker_id}
                    className={`
                      hover:bg-gray-50 cursor-pointer transition-colors
                      ${isSelected ? 'bg-blue-50' : ''}
                    `}
                    onClick={() => handleRowClick(worker.worker_id)}
                  >
                    <td
                      className="px-4 py-4"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleWorkerSelection(worker.worker_id)}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                    </td>
                    <td className="px-4 py-4">
                      <StatusCell status={worker.status} />
                    </td>
                    <td className="px-4 py-4">
                      <div>
                        <div className="font-medium text-gray-900">
                          {worker.machine_name}
                        </div>
                        <div className="text-xs text-gray-500 font-mono">
                          {worker.worker_id.slice(0, 8)}...
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      {worker.tools.length > 0 ? (
                        <ToolBadgeList
                          tools={worker.tools}
                          maxVisible={2}
                          size="sm"
                        />
                      ) : (
                        <span className="text-gray-400 text-sm">None</span>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <MetricCell
                        cpu={worker.cpu_percent}
                        memory={worker.memory_percent}
                      />
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-500">
                      {formatLastHeartbeat(worker.last_heartbeat)}
                    </td>
                    <td
                      className="px-4 py-4 text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => navigate(`/workers/${worker.worker_id}`)}
                          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                          title="View details"
                        >
                          <EyeIcon className="w-4 h-4" />
                        </button>
                        {onEdit && (
                          <button
                            onClick={() => onEdit(worker.worker_id)}
                            className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Edit"
                          >
                            <PencilIcon className="w-4 h-4" />
                          </button>
                        )}
                        {onDelete && (
                          <button
                            onClick={() => onDelete(worker.worker_id)}
                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                            title="Delete"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default WorkerTable;
