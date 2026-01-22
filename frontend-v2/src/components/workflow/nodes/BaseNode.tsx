/**
 * BaseNode - Base wrapper component for all workflow nodes
 *
 * Provides consistent styling, status indicators, and interaction handling
 * for all node types in the workflow editor.
 */

import React, { memo, type ReactNode } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { WorkflowNodeData, NodeExecutionStatus } from '@/types/workflow';
import { getStatusColor, getStatusLabel } from '@/types/workflow';

// ============================================================================
// Types
// ============================================================================

export interface BaseNodeProps {
  id: string;
  data: WorkflowNodeData;
  selected: boolean;
  children: ReactNode;
  icon: ReactNode;
  color: string;
  shape?: 'rectangle' | 'diamond' | 'hexagon' | 'rounded';
  showSourceHandle?: boolean;
  showTargetHandle?: boolean;
  sourceHandles?: { id: string; position: Position; label?: string }[];
  targetHandles?: { id: string; position: Position; label?: string }[];
}

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
    <div className="absolute -top-2 -right-2 flex items-center gap-1">
      <span
        className={`w-3 h-3 rounded-full ${statusColorClasses[status]}`}
        title={getStatusLabel(status)}
      />
      {status === 'running' && (
        <span className="text-xs text-blue-600 font-medium bg-blue-100 px-1 rounded">
          Running
        </span>
      )}
      {status === 'failed' && (
        <span className="text-xs text-red-600 font-medium bg-red-100 px-1 rounded">
          Failed
        </span>
      )}
    </div>
  );
};

// ============================================================================
// Execution Time Display
// ============================================================================

interface ExecutionTimeProps {
  startTime?: string;
  endTime?: string;
  duration?: number;
}

const ExecutionTime: React.FC<ExecutionTimeProps> = ({ startTime, endTime, duration }) => {
  if (!startTime && !duration) return null;

  let displayTime = '';
  if (duration) {
    displayTime = `${(duration / 1000).toFixed(1)}s`;
  } else if (startTime && endTime) {
    const diff = new Date(endTime).getTime() - new Date(startTime).getTime();
    displayTime = `${(diff / 1000).toFixed(1)}s`;
  } else if (startTime) {
    displayTime = 'Running...';
  }

  return (
    <div className="absolute -bottom-5 left-0 right-0 text-center">
      <span className="text-xs text-gray-500 bg-white px-1 rounded shadow-sm">
        {displayTime}
      </span>
    </div>
  );
};

// ============================================================================
// Base Node Component
// ============================================================================

export const BaseNode: React.FC<BaseNodeProps> = memo(({
  id,
  data,
  selected,
  children,
  icon,
  color,
  shape = 'rectangle',
  showSourceHandle = true,
  showTargetHandle = true,
  sourceHandles,
  targetHandles,
}) => {
  const { label, executionStatus, executionError, executionStartTime, executionEndTime, executionDuration } = data;

  // Shape-specific classes
  const shapeClasses: Record<string, string> = {
    rectangle: 'rounded-lg',
    diamond: 'rounded-lg rotate-0', // We'll use clip-path for actual diamond
    hexagon: 'rounded-lg',
    rounded: 'rounded-2xl',
  };

  // Selection and status border classes
  const getBorderClass = () => {
    if (selected) return 'ring-2 ring-blue-500 ring-offset-2';
    if (executionStatus === 'running') return 'ring-2 ring-blue-400 ring-offset-1';
    if (executionStatus === 'failed') return 'ring-2 ring-red-400 ring-offset-1';
    if (executionStatus === 'completed') return 'ring-2 ring-green-400 ring-offset-1';
    return '';
  };

  return (
    <div
      className={`
        relative bg-white shadow-lg border-2 border-gray-200
        ${shapeClasses[shape]}
        ${getBorderClass()}
        transition-all duration-200
        min-w-[180px] max-w-[280px]
      `}
      style={{ borderLeftColor: color, borderLeftWidth: '4px' }}
    >
      {/* Status Badge */}
      <StatusBadge status={executionStatus} />

      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 border-b border-gray-100"
        style={{ backgroundColor: `${color}15` }}
      >
        <span className="flex-shrink-0" style={{ color }}>
          {icon}
        </span>
        <span className="font-medium text-gray-800 text-sm truncate">
          {label}
        </span>
      </div>

      {/* Content */}
      <div className="px-3 py-2">
        {children}
      </div>

      {/* Error Display */}
      {executionError && (
        <div className="px-3 py-2 bg-red-50 border-t border-red-100">
          <p className="text-xs text-red-600 truncate" title={executionError}>
            {executionError}
          </p>
        </div>
      )}

      {/* Execution Time */}
      <ExecutionTime
        startTime={executionStartTime}
        endTime={executionEndTime}
        duration={executionDuration}
      />

      {/* Default Handles */}
      {showTargetHandle && !targetHandles && (
        <Handle
          type="target"
          position={Position.Top}
          className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors"
        />
      )}

      {showSourceHandle && !sourceHandles && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors"
        />
      )}

      {/* Custom Target Handles */}
      {targetHandles?.map((handle) => (
        <Handle
          key={handle.id}
          id={handle.id}
          type="target"
          position={handle.position}
          className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors"
        >
          {handle.label && (
            <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-xs text-gray-500 whitespace-nowrap">
              {handle.label}
            </span>
          )}
        </Handle>
      ))}

      {/* Custom Source Handles */}
      {sourceHandles?.map((handle) => (
        <Handle
          key={handle.id}
          id={handle.id}
          type="source"
          position={handle.position}
          className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors"
        >
          {handle.label && (
            <span className="absolute -bottom-4 left-1/2 -translate-x-1/2 text-xs text-gray-500 whitespace-nowrap">
              {handle.label}
            </span>
          )}
        </Handle>
      ))}
    </div>
  );
});

BaseNode.displayName = 'BaseNode';

// ============================================================================
// Node Handle Positions Helpers
// ============================================================================

export const createConditionHandles = () => ({
  targetHandles: [
    { id: 'target', position: Position.Top },
  ],
  sourceHandles: [
    { id: 'true', position: Position.Right, label: 'True' },
    { id: 'false', position: Position.Bottom, label: 'False' },
  ],
});

export const createParallelHandles = (branchCount: number) => ({
  targetHandles: [
    { id: 'target', position: Position.Top },
  ],
  sourceHandles: Array.from({ length: branchCount }, (_, i) => ({
    id: `branch-${i}`,
    position: Position.Bottom,
    label: `Branch ${i + 1}`,
  })),
});

export const createJoinHandles = (inputCount: number) => ({
  targetHandles: Array.from({ length: inputCount }, (_, i) => ({
    id: `input-${i}`,
    position: Position.Top,
    label: `Input ${i + 1}`,
  })),
  sourceHandles: [
    { id: 'source', position: Position.Bottom },
  ],
});

export const createLoopHandles = () => ({
  targetHandles: [
    { id: 'target', position: Position.Top },
  ],
  sourceHandles: [
    { id: 'loop', position: Position.Right, label: 'Loop' },
    { id: 'exit', position: Position.Bottom, label: 'Exit' },
  ],
});

export default BaseNode;
