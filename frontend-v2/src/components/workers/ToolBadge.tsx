/**
 * ToolBadge Component
 *
 * A badge component that displays an AI tool with icon, name, and status.
 */

import React from 'react';
import { ToolName, ToolStatus } from '../../types/worker';
import { getToolDisplayName } from '../../stores/workerStore';

// ============================================================================
// Types
// ============================================================================

interface ToolBadgeProps {
  tool: ToolName;
  status?: ToolStatus;
  size?: 'sm' | 'md' | 'lg';
  showStatus?: boolean;
  className?: string;
}

// ============================================================================
// Tool Icons (SVG)
// ============================================================================

const ClaudeIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
  </svg>
);

const GeminiIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
  </svg>
);

const OllamaIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h10v2H7z" />
  </svg>
);

const DefaultToolIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z" />
  </svg>
);

// ============================================================================
// Helper Functions
// ============================================================================

const getToolIcon = (tool: ToolName): React.FC<{ className?: string }> => {
  switch (tool) {
    case 'claude_code':
      return ClaudeIcon;
    case 'gemini_cli':
      return GeminiIcon;
    case 'ollama':
      return OllamaIcon;
    default:
      return DefaultToolIcon;
  }
};

const getToolColor = (tool: ToolName): string => {
  switch (tool) {
    case 'claude_code':
      return 'bg-orange-100 text-orange-700 border-orange-200';
    case 'gemini_cli':
      return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'ollama':
      return 'bg-purple-100 text-purple-700 border-purple-200';
    default:
      return 'bg-gray-100 text-gray-700 border-gray-200';
  }
};

const getStatusColor = (status: ToolStatus): string => {
  switch (status) {
    case 'available':
      return 'bg-green-500';
    case 'busy':
      return 'bg-yellow-500';
    case 'unavailable':
      return 'bg-gray-400';
    case 'error':
      return 'bg-red-500';
    default:
      return 'bg-gray-400';
  }
};

const getSizeClasses = (size: 'sm' | 'md' | 'lg'): { badge: string; icon: string; text: string; dot: string } => {
  switch (size) {
    case 'sm':
      return {
        badge: 'px-2 py-0.5 text-xs',
        icon: 'w-3 h-3',
        text: 'text-xs',
        dot: 'w-1.5 h-1.5',
      };
    case 'lg':
      return {
        badge: 'px-3 py-1.5 text-base',
        icon: 'w-5 h-5',
        text: 'text-base',
        dot: 'w-2.5 h-2.5',
      };
    case 'md':
    default:
      return {
        badge: 'px-2.5 py-1 text-sm',
        icon: 'w-4 h-4',
        text: 'text-sm',
        dot: 'w-2 h-2',
      };
  }
};

// ============================================================================
// Component
// ============================================================================

export const ToolBadge: React.FC<ToolBadgeProps> = ({
  tool,
  status,
  size = 'md',
  showStatus = false,
  className = '',
}) => {
  const Icon = getToolIcon(tool);
  const colorClass = getToolColor(tool);
  const sizeClasses = getSizeClasses(size);

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 rounded-full border font-medium
        ${colorClass}
        ${sizeClasses.badge}
        ${className}
      `}
    >
      <Icon className={sizeClasses.icon} />
      <span className={sizeClasses.text}>{getToolDisplayName(tool)}</span>
      {showStatus && status && (
        <span
          className={`${sizeClasses.dot} rounded-full ${getStatusColor(status)}`}
          title={status}
        />
      )}
    </span>
  );
};

// ============================================================================
// Compact Badge Variant
// ============================================================================

interface ToolBadgeCompactProps {
  tool: ToolName;
  className?: string;
}

export const ToolBadgeCompact: React.FC<ToolBadgeCompactProps> = ({ tool, className = '' }) => {
  const Icon = getToolIcon(tool);
  const colorClass = getToolColor(tool);

  return (
    <span
      className={`
        inline-flex items-center justify-center w-6 h-6 rounded-full
        ${colorClass}
        ${className}
      `}
      title={getToolDisplayName(tool)}
    >
      <Icon className="w-3.5 h-3.5" />
    </span>
  );
};

// ============================================================================
// Tool Badge List
// ============================================================================

interface ToolBadgeListProps {
  tools: ToolName[];
  maxVisible?: number;
  size?: 'sm' | 'md' | 'lg';
  compact?: boolean;
  className?: string;
}

export const ToolBadgeList: React.FC<ToolBadgeListProps> = ({
  tools,
  maxVisible = 3,
  size = 'sm',
  compact = false,
  className = '',
}) => {
  const visibleTools = tools.slice(0, maxVisible);
  const remainingCount = tools.length - maxVisible;

  if (compact) {
    return (
      <div className={`flex -space-x-1 ${className}`}>
        {visibleTools.map((tool) => (
          <ToolBadgeCompact key={tool} tool={tool} />
        ))}
        {remainingCount > 0 && (
          <span
            className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-200 text-gray-600 text-xs font-medium"
            title={tools.slice(maxVisible).map(getToolDisplayName).join(', ')}
          >
            +{remainingCount}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={`flex flex-wrap gap-1 ${className}`}>
      {visibleTools.map((tool) => (
        <ToolBadge key={tool} tool={tool} size={size} />
      ))}
      {remainingCount > 0 && (
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-medium cursor-default"
          title={tools.slice(maxVisible).map(getToolDisplayName).join(', ')}
        >
          +{remainingCount} more
        </span>
      )}
    </div>
  );
};

export default ToolBadge;
