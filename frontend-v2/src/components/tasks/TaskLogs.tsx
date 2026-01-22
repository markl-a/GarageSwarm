/**
 * TaskLogs Component
 *
 * Displays task execution logs with real-time streaming, filtering, and search.
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type { TaskLog } from '../../types/task';

interface TaskLogsProps {
  taskId: string;
  logs: TaskLog[];
  isStreaming?: boolean;
  onRefresh?: () => void;
  className?: string;
}

/**
 * Log level configuration
 */
type LogLevel = 'debug' | 'info' | 'warning' | 'error';

const LOG_LEVEL_CONFIG: Record<
  LogLevel,
  {
    label: string;
    color: string;
    bgColor: string;
    icon: React.ReactNode;
  }
> = {
  debug: {
    label: 'DEBUG',
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
  },
  info: {
    label: 'INFO',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  warning: {
    label: 'WARN',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  },
  error: {
    label: 'ERROR',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
};

/**
 * Log level badge component
 */
function LogLevelBadge({ level }: { level: LogLevel }) {
  const config = LOG_LEVEL_CONFIG[level];

  return (
    <span
      className={`
        inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded
        ${config.bgColor} ${config.color}
      `}
    >
      {config.icon}
      {config.label}
    </span>
  );
}

/**
 * Single log entry component
 */
function LogEntry({
  log,
  searchTerm,
}: {
  log: TaskLog;
  searchTerm: string;
}) {
  // Highlight search term in message
  const highlightedMessage = useMemo(() => {
    if (!searchTerm) return log.message;

    const regex = new RegExp(`(${searchTerm})`, 'gi');
    const parts = log.message.split(regex);

    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-yellow-200 px-0.5 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  }, [log.message, searchTerm]);

  return (
    <div className="flex items-start gap-3 py-2 px-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0">
      {/* Timestamp */}
      <span className="text-xs text-gray-500 font-mono whitespace-nowrap">
        {new Date(log.timestamp).toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          fractionalSecondDigits: 3,
        })}
      </span>

      {/* Level badge */}
      <LogLevelBadge level={log.level} />

      {/* Message */}
      <span className="flex-1 text-sm text-gray-800 font-mono break-all">
        {highlightedMessage}
      </span>

      {/* Metadata indicator */}
      {log.metadata && Object.keys(log.metadata).length > 0 && (
        <button
          className="text-gray-400 hover:text-gray-600"
          title={JSON.stringify(log.metadata, null, 2)}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      )}
    </div>
  );
}

/**
 * Empty logs state
 */
function EmptyLogs() {
  return (
    <div className="text-center py-12">
      <svg
        className="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <h3 className="mt-2 text-sm font-medium text-gray-900">No logs</h3>
      <p className="mt-1 text-sm text-gray-500">
        Task logs will appear here during execution.
      </p>
    </div>
  );
}

/**
 * Main TaskLogs component
 */
export function TaskLogs({
  taskId,
  logs,
  isStreaming = false,
  onRefresh,
  className = '',
}: TaskLogsProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilters, setLevelFilters] = useState<Set<LogLevel>>(
    new Set(['debug', 'info', 'warning', 'error'])
  );
  const [autoScroll, setAutoScroll] = useState(true);

  const logsContainerRef = useRef<HTMLDivElement>(null);
  const lastLogCountRef = useRef(logs.length);

  // Toggle level filter
  const toggleLevelFilter = useCallback((level: LogLevel) => {
    setLevelFilters((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(level)) {
        newSet.delete(level);
      } else {
        newSet.add(level);
      }
      return newSet;
    });
  }, []);

  // Filter logs based on search and level filters
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      // Level filter
      if (!levelFilters.has(log.level)) {
        return false;
      }

      // Search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        return log.message.toLowerCase().includes(searchLower);
      }

      return true;
    });
  }, [logs, levelFilters, searchTerm]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logs.length > lastLogCountRef.current && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
    lastLogCountRef.current = logs.length;
  }, [logs.length, autoScroll]);

  // Download logs as file
  const handleDownload = useCallback(() => {
    const content = filteredLogs
      .map(
        (log) =>
          `[${new Date(log.timestamp).toISOString()}] [${log.level.toUpperCase()}] ${log.message}`
      )
      .join('\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `task-${taskId}-logs.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [filteredLogs, taskId]);

  // Calculate log level counts
  const levelCounts = useMemo(() => {
    const counts: Record<LogLevel, number> = {
      debug: 0,
      info: 0,
      warning: 0,
      error: 0,
    };
    logs.forEach((log) => {
      counts[log.level]++;
    });
    return counts;
  }, [logs]);

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search logs..."
            className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Level filters */}
        <div className="flex items-center gap-2">
          {(Object.keys(LOG_LEVEL_CONFIG) as LogLevel[]).map((level) => (
            <button
              key={level}
              onClick={() => toggleLevelFilter(level)}
              className={`
                inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded border
                transition-colors
                ${
                  levelFilters.has(level)
                    ? `${LOG_LEVEL_CONFIG[level].bgColor} ${LOG_LEVEL_CONFIG[level].color} border-current`
                    : 'bg-gray-100 text-gray-400 border-gray-200'
                }
              `}
            >
              {LOG_LEVEL_CONFIG[level].label}
              <span className="ml-1 px-1 rounded bg-white/50">
                {levelCounts[level]}
              </span>
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Auto-scroll toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`
              inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md border
              ${
                autoScroll
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : 'bg-gray-50 text-gray-600 border-gray-200'
              }
            `}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            Auto-scroll
          </button>

          {/* Refresh button */}
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          )}

          {/* Download button */}
          <button
            onClick={handleDownload}
            disabled={filteredLogs.length === 0}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download
          </button>
        </div>
      </div>

      {/* Streaming indicator */}
      {isStreaming && (
        <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 text-blue-700 text-sm rounded-md mb-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
          </span>
          Streaming logs...
        </div>
      )}

      {/* Logs container */}
      <div
        ref={logsContainerRef}
        className="flex-1 min-h-[300px] max-h-[500px] overflow-y-auto bg-gray-50 border border-gray-200 rounded-lg"
      >
        {filteredLogs.length === 0 ? (
          <EmptyLogs />
        ) : (
          filteredLogs.map((log) => (
            <LogEntry key={log.id} log={log} searchTerm={searchTerm} />
          ))
        )}
      </div>

      {/* Status bar */}
      <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
        <span>
          Showing {filteredLogs.length} of {logs.length} logs
        </span>
        {searchTerm && (
          <span>
            Filter: "{searchTerm}"
          </span>
        )}
      </div>
    </div>
  );
}

export default TaskLogs;
