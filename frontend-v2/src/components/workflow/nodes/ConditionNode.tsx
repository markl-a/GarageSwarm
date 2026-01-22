/**
 * ConditionNode - Branching condition node component
 *
 * Represents a conditional branch point in the workflow with true/false outputs.
 * Styled as a diamond shape to follow flowchart conventions.
 */

import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ConditionNodeData, NodeExecutionStatus } from '@/types/workflow';
import { getStatusLabel } from '@/types/workflow';

// ============================================================================
// Icons
// ============================================================================

const GitBranchIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
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
    <div className="absolute -top-3 -right-3 z-10">
      <span
        className={`block w-3 h-3 rounded-full ${statusColorClasses[status]} border-2 border-white shadow`}
        title={getStatusLabel(status)}
      />
    </div>
  );
};

// ============================================================================
// Condition Type Display
// ============================================================================

const getConditionTypeLabel = (type: ConditionNodeData['conditionType']) => {
  switch (type) {
    case 'expression':
      return 'Expression';
    case 'status':
      return 'Status Check';
    case 'output':
      return 'Output Check';
    default:
      return 'Condition';
  }
};

const getOperatorLabel = (operator?: ConditionNodeData['operator']) => {
  switch (operator) {
    case 'equals':
      return '=';
    case 'contains':
      return 'contains';
    case 'regex':
      return 'regex';
    case 'greater':
      return '>';
    case 'less':
      return '<';
    default:
      return '';
  }
};

// ============================================================================
// ConditionNode Component
// ============================================================================

export const ConditionNode: React.FC<NodeProps<ConditionNodeData>> = memo(({ id, data, selected }) => {
  const {
    label,
    executionStatus,
    executionError,
    conditionType,
    expression,
    operator,
    expectedStatus,
    expectedOutput,
  } = data as ConditionNodeData;

  // Selection and status border classes
  const getBorderClass = () => {
    if (selected) return 'ring-2 ring-blue-500 ring-offset-2';
    if (executionStatus === 'running') return 'ring-2 ring-blue-400 ring-offset-1';
    if (executionStatus === 'failed') return 'ring-2 ring-red-400 ring-offset-1';
    if (executionStatus === 'completed') return 'ring-2 ring-green-400 ring-offset-1';
    return '';
  };

  // Diamond shape container
  return (
    <div className="relative">
      {/* Status Badge */}
      <StatusBadge status={executionStatus} />

      {/* Diamond Container */}
      <div
        className={`
          relative bg-white shadow-lg
          w-[160px] h-[160px]
          transform rotate-45
          border-2 border-amber-400
          ${getBorderClass()}
          transition-all duration-200
        `}
        style={{ borderRadius: '12px' }}
      >
        {/* Inner Content (counter-rotated) */}
        <div className="absolute inset-0 transform -rotate-45 flex flex-col items-center justify-center p-4">
          {/* Header */}
          <div className="flex items-center gap-1 text-amber-600 mb-1">
            <GitBranchIcon />
            <span className="font-medium text-sm">{label}</span>
          </div>

          {/* Condition Type */}
          <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full mb-1">
            {getConditionTypeLabel(conditionType)}
          </span>

          {/* Condition Preview */}
          <div className="text-xs text-gray-600 text-center max-w-[100px]">
            {conditionType === 'expression' && expression && (
              <span className="font-mono truncate block">{expression.length > 20 ? `${expression.substring(0, 20)}...` : expression}</span>
            )}
            {conditionType === 'status' && expectedStatus && (
              <span>Status {getOperatorLabel(operator)} {expectedStatus}</span>
            )}
            {conditionType === 'output' && expectedOutput && (
              <span>{getOperatorLabel(operator)} "{expectedOutput.length > 10 ? `${expectedOutput.substring(0, 10)}...` : expectedOutput}"</span>
            )}
          </div>

          {/* Error Display */}
          {executionError && (
            <div className="mt-1 text-xs text-red-600 text-center truncate max-w-[100px]" title={executionError}>
              Error
            </div>
          )}
        </div>
      </div>

      {/* Handles - positioned outside the diamond rotation */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors !-top-1"
        style={{ left: '50%', transform: 'translateX(-50%)' }}
      />

      {/* True Handle (Right) */}
      <Handle
        type="source"
        id="true"
        position={Position.Right}
        className="!w-3 !h-3 !bg-green-500 !border-2 !border-white hover:!bg-green-600 transition-colors"
        style={{ top: '50%', transform: 'translateY(-50%)', right: '-6px' }}
      />
      <span
        className="absolute text-xs text-green-600 font-medium"
        style={{ top: '50%', right: '-30px', transform: 'translateY(-50%)' }}
      >
        True
      </span>

      {/* False Handle (Bottom) */}
      <Handle
        type="source"
        id="false"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-red-500 !border-2 !border-white hover:!bg-red-600 transition-colors !-bottom-1"
        style={{ left: '50%', transform: 'translateX(-50%)' }}
      />
      <span
        className="absolute text-xs text-red-600 font-medium"
        style={{ bottom: '-20px', left: '50%', transform: 'translateX(-50%)' }}
      >
        False
      </span>
    </div>
  );
});

ConditionNode.displayName = 'ConditionNode';

export default ConditionNode;
