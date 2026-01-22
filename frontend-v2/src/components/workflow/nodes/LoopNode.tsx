/**
 * LoopNode - Loop node component
 *
 * Represents a loop construct that can iterate a fixed number of times,
 * while a condition is true, or for each item in a collection.
 */

import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { LoopNodeData, NodeExecutionStatus } from '@/types/workflow';
import { getStatusLabel } from '@/types/workflow';

// ============================================================================
// Icons
// ============================================================================

const RepeatIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const LoopArrowIcon = () => (
  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8V4l4 4-4 4V8zM12 8a4 4 0 100 8 4 4 0 000-8z" />
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
// Loop Type Display
// ============================================================================

const getLoopTypeLabel = (type: LoopNodeData['loopType']) => {
  switch (type) {
    case 'count':
      return 'Count';
    case 'while':
      return 'While';
    case 'for_each':
      return 'For Each';
    default:
      return 'Loop';
  }
};

const getLoopDescription = (data: LoopNodeData) => {
  const { loopType, countValue, whileCondition, forEachSource, forEachVariable } = data;

  switch (loopType) {
    case 'count':
      return `${countValue || 0} iterations`;
    case 'while':
      return whileCondition ? (whileCondition.length > 20 ? `${whileCondition.substring(0, 20)}...` : whileCondition) : 'condition';
    case 'for_each':
      return forEachSource && forEachVariable
        ? `${forEachVariable} in ${forEachSource.length > 15 ? `${forEachSource.substring(0, 15)}...` : forEachSource}`
        : 'items';
    default:
      return '';
  }
};

// ============================================================================
// LoopNode Component
// ============================================================================

export const LoopNode: React.FC<NodeProps<LoopNodeData>> = memo(({ id, data, selected }) => {
  const {
    label,
    executionStatus,
    executionError,
    loopType,
    maxIterations,
    currentIteration,
  } = data as LoopNodeData;

  // Selection and status border classes
  const getBorderClass = () => {
    if (selected) return 'ring-2 ring-blue-500 ring-offset-2';
    if (executionStatus === 'running') return 'ring-2 ring-blue-400 ring-offset-1';
    if (executionStatus === 'failed') return 'ring-2 ring-red-400 ring-offset-1';
    if (executionStatus === 'completed') return 'ring-2 ring-green-400 ring-offset-1';
    return '';
  };

  // Progress calculation
  const progress = currentIteration && maxIterations
    ? Math.min((currentIteration / maxIterations) * 100, 100)
    : 0;

  return (
    <div className="relative">
      {/* Status Badge */}
      <StatusBadge status={executionStatus} />

      {/* Main Container */}
      <div
        className={`
          relative bg-white shadow-lg
          border-2 border-orange-400
          rounded-lg
          min-w-[180px] max-w-[220px]
          ${getBorderClass()}
          transition-all duration-200
        `}
        style={{ borderLeftWidth: '4px', borderLeftColor: '#F97316' }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 bg-orange-50">
          <span className="text-orange-600">
            <RepeatIcon />
          </span>
          <span className="font-medium text-gray-800 text-sm truncate">{label}</span>
        </div>

        {/* Content */}
        <div className="px-3 py-2 space-y-2">
          {/* Loop Icon and Type */}
          <div className="flex items-center justify-center gap-2">
            <div className="p-2 bg-orange-100 rounded-lg">
              <span className="text-orange-600">
                <LoopArrowIcon />
              </span>
            </div>
            <div className="text-center">
              <span className="text-xs px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full block">
                {getLoopTypeLabel(loopType)}
              </span>
              <span className="text-xs text-gray-600 mt-0.5 block">
                {getLoopDescription(data as LoopNodeData)}
              </span>
            </div>
          </div>

          {/* Iteration Progress */}
          {executionStatus === 'running' && currentIteration !== undefined && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-gray-600">
                <span>Iteration {currentIteration}</span>
                <span>Max: {maxIterations}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-orange-500 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Configuration Badges */}
          <div className="flex flex-wrap gap-1 justify-center">
            <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
              Max: {maxIterations}
            </span>
            {currentIteration !== undefined && executionStatus !== 'running' && (
              <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-600 rounded">
                Ran: {currentIteration}x
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

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors"
      />

      {/* Loop Back Handle (Right) */}
      <Handle
        type="source"
        id="loop"
        position={Position.Right}
        className="!w-3 !h-3 !bg-orange-500 !border-2 !border-white hover:!bg-orange-600 transition-colors"
      />
      <span
        className="absolute text-xs text-orange-600 font-medium"
        style={{ top: '50%', right: '-32px', transform: 'translateY(-50%)' }}
      >
        Loop
      </span>

      {/* Exit Handle (Bottom) */}
      <Handle
        type="source"
        id="exit"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors"
      />
      <span
        className="absolute text-xs text-gray-600 font-medium"
        style={{ bottom: '-18px', left: '50%', transform: 'translateX(-50%)' }}
      >
        Exit
      </span>
    </div>
  );
});

LoopNode.displayName = 'LoopNode';

export default LoopNode;
