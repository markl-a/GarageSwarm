/**
 * TaskNode - Task execution node component
 *
 * Represents a task that executes with an AI tool (Claude Code, Gemini CLI, etc.)
 */

import React, { memo } from 'react';
import { type NodeProps } from '@xyflow/react';
import type { TaskNodeData } from '@/types/workflow';
import { AVAILABLE_TOOLS } from '@/types/workflow';
import { BaseNode } from './BaseNode';

// ============================================================================
// Icons
// ============================================================================

const PlayIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const TerminalIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
  </svg>
);

const SparklesIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
);

const CpuIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
  </svg>
);

const CommandLineIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3" />
  </svg>
);

const GlobeIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const FolderIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
  </svg>
);

// ============================================================================
// Tool Icon Mapping
// ============================================================================

const getToolIcon = (toolId: string) => {
  switch (toolId) {
    case 'claude_code':
      return <TerminalIcon />;
    case 'gemini_cli':
      return <SparklesIcon />;
    case 'ollama':
      return <CpuIcon />;
    case 'shell':
      return <CommandLineIcon />;
    case 'http':
      return <GlobeIcon />;
    case 'file':
      return <FolderIcon />;
    default:
      return <TerminalIcon />;
  }
};

const getToolName = (toolId: string) => {
  const tool = AVAILABLE_TOOLS.find(t => t.id === toolId);
  return tool?.name || toolId;
};

// ============================================================================
// TaskNode Component
// ============================================================================

export const TaskNode: React.FC<NodeProps<TaskNodeData>> = memo(({ id, data, selected }) => {
  const { tool, prompt, timeout, retryCount, outputVariable } = data as TaskNodeData;

  return (
    <BaseNode
      id={id}
      data={data}
      selected={selected}
      icon={<PlayIcon />}
      color="#3B82F6"
      shape="rectangle"
    >
      <div className="space-y-2">
        {/* Tool Badge */}
        <div className="flex items-center gap-1.5 text-xs">
          <span className="flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
            {getToolIcon(tool)}
            {getToolName(tool)}
          </span>
        </div>

        {/* Prompt Preview */}
        {prompt && (
          <div className="text-xs text-gray-600 line-clamp-2 bg-gray-50 p-1.5 rounded">
            {prompt.length > 80 ? `${prompt.substring(0, 80)}...` : prompt}
          </div>
        )}

        {/* Configuration Badges */}
        <div className="flex flex-wrap gap-1">
          {timeout && (
            <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
              Timeout: {timeout}s
            </span>
          )}
          {retryCount && retryCount > 0 && (
            <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
              Retries: {retryCount}
            </span>
          )}
          {outputVariable && (
            <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded">
              ${outputVariable}
            </span>
          )}
        </div>
      </div>
    </BaseNode>
  );
});

TaskNode.displayName = 'TaskNode';

export default TaskNode;
