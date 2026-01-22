/**
 * JoinNode - Join/merge node component
 *
 * Represents a point where multiple parallel branches merge back together.
 */

import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { JoinNodeData, NodeExecutionStatus } from '@/types/workflow';
import { getStatusLabel } from '@/types/workflow';

// ============================================================================
// Icons
// ============================================================================

const GitMergeIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
);

const MergeArrowsIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 4l6 8M18 4l-6 8M12 12v8" />
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
// Join Type Display
// ============================================================================

const getJoinTypeLabel = (type: JoinNodeData['joinType'], minRequired?: number) => {
  switch (type) {
    case 'all':
      return 'Wait for All';
    case 'any':
      return 'First to Complete';
    case 'n_of_m':
      return `${minRequired || 1} Required`;
    default:
      return 'Join';
  }
};

// ============================================================================
// JoinNode Component
// ============================================================================

export const JoinNode: React.FC<NodeProps<JoinNodeData>> = memo(({ id, data, selected }) => {
  const {
    label,
    executionStatus,
    executionError,
    joinType,
    minRequired,
    timeout,
  } = data as JoinNodeData;

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
          border-2 border-indigo-400
          rounded-lg
          min-w-[160px]
          ${getBorderClass()}
          transition-all duration-200
        `}
        style={{ borderLeftWidth: '4px', borderLeftColor: '#6366F1' }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 bg-indigo-50">
          <span className="text-indigo-600">
            <GitMergeIcon />
          </span>
          <span className="font-medium text-gray-800 text-sm">{label}</span>
        </div>

        {/* Content */}
        <div className="px-3 py-2 space-y-2">
          {/* Merge Icon */}
          <div className="flex justify-center">
            <div className="p-2 bg-indigo-100 rounded-lg">
              <span className="text-indigo-600">
                <MergeArrowsIcon />
              </span>
            </div>
          </div>

          {/* Configuration */}
          <div className="flex flex-wrap gap-1 justify-center">
            <span className="text-xs px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded">
              {getJoinTypeLabel(joinType, minRequired)}
            </span>
            {timeout && (
              <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                Timeout: {timeout}s
              </span>
            )}
          </div>

          {/* Error Display */}
          {executionError && (
            <div className="text-xs text-red-600 text-center truncate" title={executionError}>
              {executionError}
            </div>
          )}
        </div>
      </div>

      {/* Multiple target handles for incoming branches */}
      <Handle
        type="target"
        id="input-1"
        position={Position.Top}
        className="!w-3 !h-3 !bg-indigo-500 !border-2 !border-white hover:!bg-indigo-600 transition-colors"
        style={{ left: '25%' }}
      />
      <Handle
        type="target"
        id="input-2"
        position={Position.Top}
        className="!w-3 !h-3 !bg-indigo-500 !border-2 !border-white hover:!bg-indigo-600 transition-colors"
        style={{ left: '50%' }}
      />
      <Handle
        type="target"
        id="input-3"
        position={Position.Top}
        className="!w-3 !h-3 !bg-indigo-500 !border-2 !border-white hover:!bg-indigo-600 transition-colors"
        style={{ left: '75%' }}
      />

      {/* Single source handle for merged output */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors"
      />
    </div>
  );
});

JoinNode.displayName = 'JoinNode';

export default JoinNode;
