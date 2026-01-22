/**
 * ParallelNode - Parallel split node component
 *
 * Represents a point where execution splits into multiple parallel branches.
 */

import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ParallelNodeData, NodeExecutionStatus } from '@/types/workflow';
import { getStatusLabel } from '@/types/workflow';

// ============================================================================
// Icons
// ============================================================================

const GitForkIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

const ParallelLinesIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 6v12M12 6v12M18 6v12" />
  </svg>
);

// ============================================================================
// Status Badge Component
// ============================================================================

interface StatusBadgeProps {
  status: NodeExecutionStatus;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  if (status === 'idle') return null;

  const statusColorClasses: Record<NodeExecutionStatus, string> = {
    idle: 'bg-gray-400',
    pending: 'bg-yellow-400 animate-pulse',
    running: 'bg-blue-500 animate-pulse',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    skipped: 'bg-gray-400',
    waiting_approval: 'bg-purple-500 animate-pulse',
  };

  return (
    <div className="absolute -top-2 -right-2 z-10">
      <span
        className={`block w-3 h-3 rounded-full ${statusColorClasses[status]} border-2 border-white shadow`}
        title={getStatusLabel(status)}
      />
    </div>
  );
};

// ============================================================================
// ParallelNode Component
// ============================================================================

export const ParallelNode: React.FC<NodeProps<ParallelNodeData>> = memo(({ id, data, selected }) => {
  const {
    label,
    executionStatus,
    executionError,
    maxConcurrency,
    waitForAll,
  } = data as ParallelNodeData;

  // Selection and status border classes
  const getBorderClass = () => {
    if (selected) return 'ring-2 ring-blue-500 ring-offset-2';
    if (executionStatus === 'running') return 'ring-2 ring-blue-400 ring-offset-1';
    if (executionStatus === 'failed') return 'ring-2 ring-red-400 ring-offset-1';
    if (executionStatus === 'completed') return 'ring-2 ring-green-400 ring-offset-1';
    return '';
  };

  return (
    <div className="relative">
      {/* Status Badge */}
      <StatusBadge status={executionStatus} />

      {/* Main Container */}
      <div
        className={`
          relative bg-white shadow-lg
          border-2 border-teal-400
          rounded-lg
          min-w-[160px]
          ${getBorderClass()}
          transition-all duration-200
        `}
        style={{ borderLeftWidth: '4px', borderLeftColor: '#14B8A6' }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 bg-teal-50">
          <span className="text-teal-600">
            <GitForkIcon />
          </span>
          <span className="font-medium text-gray-800 text-sm">{label}</span>
        </div>

        {/* Content */}
        <div className="px-3 py-2 space-y-2">
          {/* Parallel Icon */}
          <div className="flex justify-center">
            <div className="p-2 bg-teal-100 rounded-lg">
              <span className="text-teal-600">
                <ParallelLinesIcon />
              </span>
            </div>
          </div>

          {/* Configuration */}
          <div className="flex flex-wrap gap-1 justify-center">
            {maxConcurrency && (
              <span className="text-xs px-1.5 py-0.5 bg-teal-100 text-teal-700 rounded">
                Max: {maxConcurrency}
              </span>
            )}
            <span className={`text-xs px-1.5 py-0.5 rounded ${waitForAll ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
              {waitForAll ? 'Wait All' : 'Race'}
            </span>
          </div>

          {/* Error Display */}
          {executionError && (
            <div className="text-xs text-red-600 text-center truncate" title={executionError}>
              {executionError}
            </div>
          )}
        </div>
      </div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors"
      />

      {/* Multiple source handles for parallel branches */}
      <Handle
        type="source"
        id="branch-1"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-teal-500 !border-2 !border-white hover:!bg-teal-600 transition-colors"
        style={{ left: '25%' }}
      />
      <Handle
        type="source"
        id="branch-2"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-teal-500 !border-2 !border-white hover:!bg-teal-600 transition-colors"
        style={{ left: '50%' }}
      />
      <Handle
        type="source"
        id="branch-3"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-teal-500 !border-2 !border-white hover:!bg-teal-600 transition-colors"
        style={{ left: '75%' }}
      />
    </div>
  );
});

ParallelNode.displayName = 'ParallelNode';

export default ParallelNode;
