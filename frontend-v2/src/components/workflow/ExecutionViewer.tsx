/**
 * ExecutionViewer - Execution visualization component
 *
 * Displays the execution status, logs, and progress of workflow runs.
 * Shows node status overlays, execution path highlighting, and detailed logs.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import type { NodeExecutionLog, WorkflowExecutionStatus, NodeExecutionStatus } from '@/types/workflow';
import { getStatusColor, getStatusLabel } from '@/types/workflow';
import { useWorkflowStore, useIsExecuting, useExecutionStatus } from '@/stores/workflowStore';

// ============================================================================
// Icons
// ============================================================================

const PlayIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const PauseIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const StopIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
  </svg>
);

const ChevronUpIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
  </svg>
);

const ChevronDownIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const TrashIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

// ============================================================================
// Status Badge Component
// ============================================================================

interface StatusBadgeProps {
  status: WorkflowExecutionStatus | NodeExecutionStatus;
  size?: 'sm' | 'md';
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm' }) => {
  const colorClasses: Record<string, string> = {
    idle: 'bg-gray-100 text-gray-700',
    pending: 'bg-yellow-100 text-yellow-700',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    skipped: 'bg-gray-100 text-gray-500',
    waiting_approval: 'bg-purple-100 text-purple-700',
    paused: 'bg-orange-100 text-orange-700',
    cancelled: 'bg-gray-100 text-gray-700',
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';

  return (
    <span className={`${colorClasses[status] || colorClasses.idle} ${sizeClasses} rounded-full font-medium`}>
      {getStatusLabel(status as NodeExecutionStatus) || status}
    </span>
  );
};

// ============================================================================
// Log Entry Component
// ============================================================================

interface LogEntryProps {
  log: NodeExecutionLog;
  onNodeClick: (nodeId: string) => void;
}

const LogEntry: React.FC<LogEntryProps> = ({ log, onNodeClick }) => {
  const levelColors: Record<NodeExecutionLog['level'], string> = {
    info: 'text-blue-500',
    warning: 'text-yellow-500',
    error: 'text-red-500',
    debug: 'text-gray-400',
  };

  const levelIcons: Record<NodeExecutionLog['level'], string> = {
    info: 'I',
    warning: 'W',
    error: 'E',
    debug: 'D',
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  return (
    <div className="flex items-start gap-2 py-1.5 px-2 hover:bg-gray-50 font-mono text-xs">
      <span className="text-gray-400 flex-shrink-0">{formatTime(log.timestamp)}</span>
      <span className={`${levelColors[log.level]} font-bold flex-shrink-0 w-4`}>
        {levelIcons[log.level]}
      </span>
      <button
        onClick={() => onNodeClick(log.nodeId)}
        className="text-gray-500 hover:text-blue-500 flex-shrink-0 underline"
      >
        {log.nodeId.substring(0, 8)}
      </button>
      <span className="text-gray-700 break-all">{log.message}</span>
    </div>
  );
};

// ============================================================================
// Progress Bar Component
// ============================================================================

interface ProgressBarProps {
  completed: number;
  total: number;
  running: boolean;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ completed, total, running }) => {
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{completed} / {total} nodes</span>
        <span>{percentage}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${running ? 'bg-blue-500' : 'bg-green-500'}`}
          style={{ width: `${percentage}%` }}
        >
          {running && (
            <div className="h-full w-full bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Node Status Summary Component
// ============================================================================

interface NodeStatusSummaryProps {
  nodes: { status: NodeExecutionStatus }[];
}

const NodeStatusSummary: React.FC<NodeStatusSummaryProps> = ({ nodes }) => {
  const counts = nodes.reduce(
    (acc, node) => {
      acc[node.status] = (acc[node.status] || 0) + 1;
      return acc;
    },
    {} as Record<NodeExecutionStatus, number>
  );

  const statusOrder: NodeExecutionStatus[] = ['running', 'pending', 'completed', 'failed', 'skipped', 'waiting_approval', 'idle'];

  return (
    <div className="flex flex-wrap gap-2">
      {statusOrder.map((status) => {
        const count = counts[status];
        if (!count) return null;

        return (
          <div key={status} className="flex items-center gap-1">
            <span
              className={`w-2 h-2 rounded-full ${
                status === 'running' ? 'bg-blue-500 animate-pulse' :
                status === 'pending' ? 'bg-yellow-400' :
                status === 'completed' ? 'bg-green-500' :
                status === 'failed' ? 'bg-red-500' :
                status === 'waiting_approval' ? 'bg-purple-500' :
                'bg-gray-400'
              }`}
            />
            <span className="text-xs text-gray-600">{count}</span>
          </div>
        );
      })}
    </div>
  );
};

// ============================================================================
// ExecutionViewer Component
// ============================================================================

interface ExecutionViewerProps {
  isOpen: boolean;
  onToggle: () => void;
}

export const ExecutionViewer: React.FC<ExecutionViewerProps> = ({ isOpen, onToggle }) => {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [selectedLogLevel, setSelectedLogLevel] = useState<NodeExecutionLog['level'] | 'all'>('all');

  const isExecuting = useIsExecuting();
  const executionStatus = useExecutionStatus();
  const {
    execution,
    executionLogs,
    nodes,
    startExecution,
    pauseExecution,
    resumeExecution,
    stopExecution,
    clearExecutionLogs,
    selectNode,
  } = useWorkflowStore();

  // Auto-scroll to bottom when new logs appear
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [executionLogs, autoScroll]);

  // Filter logs by level
  const filteredLogs = selectedLogLevel === 'all'
    ? executionLogs
    : executionLogs.filter((log) => log.level === selectedLogLevel);

  // Handle node click from log
  const handleNodeClick = useCallback((nodeId: string) => {
    selectNode(nodeId);
  }, [selectNode]);

  // Calculate completed nodes count
  const completedNodes = nodes.filter(
    (n) => n.data.executionStatus === 'completed' || n.data.executionStatus === 'failed'
  ).length;

  // Execution duration
  const getDuration = () => {
    if (!execution?.startTime) return '0s';
    const start = new Date(execution.startTime).getTime();
    const end = execution.endTime ? new Date(execution.endTime).getTime() : Date.now();
    const seconds = Math.floor((end - start) / 1000);
    const minutes = Math.floor(seconds / 60);
    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    }
    return `${seconds}s`;
  };

  if (!isOpen) {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-50">
        <button
          onClick={onToggle}
          className="mx-auto block px-4 py-2 bg-white border border-gray-200 border-b-0 rounded-t-lg shadow-lg hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <ChevronUpIcon />
            <span>Execution Log</span>
            {isExecuting && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                <span className="text-blue-600">Running</span>
              </span>
            )}
          </div>
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-4">
          <h3 className="font-semibold text-gray-800">Execution</h3>
          <StatusBadge status={executionStatus} size="md" />
          {isExecuting && (
            <span className="text-sm text-gray-500">{getDuration()}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Execution Controls */}
          {!isExecuting ? (
            <button
              onClick={startExecution}
              disabled={nodes.length === 0}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-green-500 hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed rounded-lg transition-colors"
            >
              <PlayIcon />
              Run
            </button>
          ) : (
            <>
              {executionStatus === 'paused' ? (
                <button
                  onClick={resumeExecution}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-500 hover:bg-blue-600 rounded-lg transition-colors"
                >
                  <PlayIcon />
                  Resume
                </button>
              ) : (
                <button
                  onClick={pauseExecution}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 rounded-lg transition-colors"
                >
                  <PauseIcon />
                  Pause
                </button>
              )}
              <button
                onClick={stopExecution}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors"
              >
                <StopIcon />
                Stop
              </button>
            </>
          )}

          <div className="w-px h-6 bg-gray-300" />

          <button
            onClick={clearExecutionLogs}
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded transition-colors"
            title="Clear Logs"
          >
            <TrashIcon />
          </button>

          <button
            onClick={onToggle}
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded transition-colors"
            title="Collapse"
          >
            <ChevronDownIcon />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex h-64">
        {/* Left Panel: Status & Progress */}
        <div className="w-64 border-r border-gray-200 p-4 flex flex-col gap-4">
          {/* Progress */}
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">Progress</h4>
            <ProgressBar
              completed={completedNodes}
              total={nodes.length}
              running={isExecuting}
            />
          </div>

          {/* Node Status Summary */}
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">Node Status</h4>
            <NodeStatusSummary nodes={nodes.map((n) => ({ status: n.data.executionStatus }))} />
          </div>

          {/* Current Node */}
          {execution?.currentNodeId && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">Current Node</h4>
              <button
                onClick={() => handleNodeClick(execution.currentNodeId!)}
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                {nodes.find((n) => n.id === execution.currentNodeId)?.data.label || execution.currentNodeId}
              </button>
            </div>
          )}
        </div>

        {/* Right Panel: Logs */}
        <div className="flex-1 flex flex-col">
          {/* Log Toolbar */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 bg-gray-50">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Filter:</span>
              <select
                value={selectedLogLevel}
                onChange={(e) => setSelectedLogLevel(e.target.value as NodeExecutionLog['level'] | 'all')}
                className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">All</option>
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
                <option value="debug">Debug</option>
              </select>
            </div>
            <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="w-3 h-3"
              />
              Auto-scroll
            </label>
          </div>

          {/* Log Content */}
          <div className="flex-1 overflow-y-auto bg-gray-900 text-gray-100">
            {filteredLogs.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>No logs yet. Run the workflow to see execution logs.</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-800">
                {filteredLogs.map((log, index) => (
                  <LogEntry key={index} log={log} onNodeClick={handleNodeClick} />
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExecutionViewer;
