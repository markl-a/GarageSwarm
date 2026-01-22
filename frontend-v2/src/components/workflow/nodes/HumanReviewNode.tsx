/**
 * HumanReviewNode - Human review gate node component
 *
 * Represents a point where workflow execution pauses for human approval,
 * input, or choice.
 */

import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { HumanReviewNodeData, NodeExecutionStatus } from '@/types/workflow';
import { getStatusLabel } from '@/types/workflow';

// ============================================================================
// Icons
// ============================================================================

const UserCheckIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 8l-3 3-1.5-1.5" />
  </svg>
);

const ClipboardCheckIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
  </svg>
);

const EditIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
  </svg>
);

const ListIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
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
// Review Type Display
// ============================================================================

const getReviewTypeIcon = (type: HumanReviewNodeData['reviewType']) => {
  switch (type) {
    case 'approval':
      return <ClipboardCheckIcon />;
    case 'input':
      return <EditIcon />;
    case 'choice':
      return <ListIcon />;
    default:
      return <ClipboardCheckIcon />;
  }
};

const getReviewTypeLabel = (type: HumanReviewNodeData['reviewType']) => {
  switch (type) {
    case 'approval':
      return 'Approval';
    case 'input':
      return 'Input Required';
    case 'choice':
      return 'Choice';
    default:
      return 'Review';
  }
};

// ============================================================================
// HumanReviewNode Component
// ============================================================================

export const HumanReviewNode: React.FC<NodeProps<HumanReviewNodeData>> = memo(({ id, data, selected }) => {
  const {
    label,
    executionStatus,
    executionError,
    reviewType,
    instructions,
    choices,
    timeoutAction,
    timeoutMinutes,
    assigneeEmail,
  } = data as HumanReviewNodeData;

  // Selection and status border classes
  const getBorderClass = () => {
    if (selected) return 'ring-2 ring-blue-500 ring-offset-2';
    if (executionStatus === 'waiting_approval') return 'ring-2 ring-purple-400 ring-offset-1 animate-pulse';
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
          border-2 border-purple-400
          rounded-xl
          min-w-[180px] max-w-[240px]
          ${getBorderClass()}
          transition-all duration-200
        `}
        style={{ borderLeftWidth: '4px', borderLeftColor: '#A855F7' }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 bg-purple-50 rounded-t-xl">
          <span className="text-purple-600">
            <UserCheckIcon />
          </span>
          <span className="font-medium text-gray-800 text-sm truncate">{label}</span>
        </div>

        {/* Content */}
        <div className="px-3 py-2 space-y-2">
          {/* Review Type Icon */}
          <div className="flex items-center justify-center gap-2">
            <div className="p-2 bg-purple-100 rounded-lg">
              <span className="text-purple-600">
                {getReviewTypeIcon(reviewType)}
              </span>
            </div>
            <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">
              {getReviewTypeLabel(reviewType)}
            </span>
          </div>

          {/* Instructions Preview */}
          {instructions && (
            <div className="text-xs text-gray-600 line-clamp-2 bg-gray-50 p-1.5 rounded">
              {instructions.length > 60 ? `${instructions.substring(0, 60)}...` : instructions}
            </div>
          )}

          {/* Choices Preview */}
          {reviewType === 'choice' && choices && choices.length > 0 && (
            <div className="space-y-0.5">
              {choices.slice(0, 3).map((choice, index) => (
                <div key={index} className="text-xs px-2 py-0.5 bg-gray-100 rounded truncate">
                  {choice}
                </div>
              ))}
              {choices.length > 3 && (
                <div className="text-xs text-gray-500 px-2">
                  +{choices.length - 3} more
                </div>
              )}
            </div>
          )}

          {/* Configuration Badges */}
          <div className="flex flex-wrap gap-1">
            {assigneeEmail && (
              <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded truncate max-w-full">
                @{assigneeEmail.split('@')[0]}
              </span>
            )}
            {timeoutMinutes && (
              <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                {timeoutMinutes}m timeout
              </span>
            )}
            {timeoutAction && timeoutMinutes && (
              <span className="text-xs px-1.5 py-0.5 bg-orange-100 text-orange-600 rounded">
                Auto: {timeoutAction}
              </span>
            )}
          </div>

          {/* Waiting for Approval Indicator */}
          {executionStatus === 'waiting_approval' && (
            <div className="flex items-center justify-center gap-1 text-purple-600 bg-purple-100 rounded-lg py-1">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-xs font-medium">Waiting...</span>
            </div>
          )}

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

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white hover:!bg-blue-500 transition-colors"
      />
    </div>
  );
});

HumanReviewNode.displayName = 'HumanReviewNode';

export default HumanReviewNode;
