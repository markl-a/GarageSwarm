/**
 * TaskTimeline Component
 *
 * Displays execution timeline with status transitions and duration calculations.
 */

import React, { useMemo } from 'react';
import type { Task, TaskStatus, TaskTimelineEvent } from '../../types/task';
import { getStatusConfig, calculateDuration, formatTimestamp } from '../../types/task';

interface TaskTimelineProps {
  task: Task;
  className?: string;
}

/**
 * Timeline step configuration
 */
interface TimelineStep {
  status: TaskStatus;
  label: string;
  timestamp: string | null;
  isActive: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  duration?: string | null;
}

/**
 * Status order for timeline display
 */
const STATUS_ORDER: TaskStatus[] = [
  'pending',
  'queued',
  'assigned',
  'running',
  'completed',
];

/**
 * Get status index in the timeline
 */
function getStatusIndex(status: TaskStatus): number {
  if (status === 'failed' || status === 'cancelled') {
    // Failed/cancelled can happen after any status
    return STATUS_ORDER.length;
  }
  return STATUS_ORDER.indexOf(status);
}

/**
 * Timeline icon component
 */
function TimelineIcon({
  status,
  isActive,
  isCompleted,
  isFailed,
}: {
  status: TaskStatus;
  isActive: boolean;
  isCompleted: boolean;
  isFailed: boolean;
}) {
  const config = getStatusConfig(status);

  if (isFailed) {
    return (
      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100 border-2 border-red-500">
        <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
    );
  }

  if (isCompleted) {
    return (
      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-green-100 border-2 border-green-500">
        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
    );
  }

  if (isActive) {
    return (
      <div
        className={`
          flex items-center justify-center w-8 h-8 rounded-full
          ${config.bgColor} border-2 ${config.borderColor}
          ${config.pulseAnimation ? 'animate-pulse' : ''}
        `}
      >
        <div className={`w-3 h-3 rounded-full ${config.color.replace('text-', 'bg-')}`} />
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 border-2 border-gray-300">
      <div className="w-3 h-3 rounded-full bg-gray-300" />
    </div>
  );
}

/**
 * Timeline connector line
 */
function TimelineConnector({
  isCompleted,
  isActive,
}: {
  isCompleted: boolean;
  isActive: boolean;
}) {
  return (
    <div
      className={`
        absolute left-4 top-10 w-0.5 h-full -translate-x-1/2
        ${isCompleted ? 'bg-green-500' : isActive ? 'bg-blue-300' : 'bg-gray-200'}
      `}
    />
  );
}

/**
 * Single timeline step component
 */
function TimelineStep({
  step,
  isLast,
}: {
  step: TimelineStep;
  isLast: boolean;
}) {
  const config = getStatusConfig(step.status);

  return (
    <div className="relative pb-8 last:pb-0">
      {/* Connector line */}
      {!isLast && (
        <TimelineConnector
          isCompleted={step.isCompleted && !step.isFailed}
          isActive={step.isActive}
        />
      )}

      <div className="flex items-start gap-4">
        {/* Icon */}
        <TimelineIcon
          status={step.status}
          isActive={step.isActive}
          isCompleted={step.isCompleted}
          isFailed={step.isFailed}
        />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4
              className={`
                text-sm font-medium
                ${step.isActive ? config.color : step.isCompleted ? 'text-gray-900' : 'text-gray-500'}
              `}
            >
              {step.label}
            </h4>
            {step.duration && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                {step.duration}
              </span>
            )}
          </div>

          {step.timestamp ? (
            <p className="text-xs text-gray-500 mt-0.5">
              {formatTimestamp(step.timestamp)}
            </p>
          ) : (
            <p className="text-xs text-gray-400 mt-0.5 italic">
              {step.isActive ? 'In progress...' : 'Pending'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Compact timeline for inline display
 */
export function TaskTimelineCompact({ task, className = '' }: TaskTimelineProps) {
  const currentStatusIndex = getStatusIndex(task.status);
  const isFailed = task.status === 'failed' || task.status === 'cancelled';

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {STATUS_ORDER.map((status, index) => {
        const isCompleted = index < currentStatusIndex || (index === currentStatusIndex && task.status === 'completed');
        const isActive = index === currentStatusIndex && !isFailed && task.status !== 'completed';
        const config = getStatusConfig(status);

        return (
          <React.Fragment key={status}>
            {/* Status dot */}
            <div
              className={`
                w-2.5 h-2.5 rounded-full
                ${
                  isCompleted
                    ? 'bg-green-500'
                    : isActive
                    ? `${config.color.replace('text-', 'bg-')} animate-pulse`
                    : 'bg-gray-300'
                }
              `}
              title={config.label}
            />
            {/* Connector */}
            {index < STATUS_ORDER.length - 1 && (
              <div
                className={`
                  w-4 h-0.5
                  ${isCompleted ? 'bg-green-500' : 'bg-gray-200'}
                `}
              />
            )}
          </React.Fragment>
        );
      })}

      {/* Failed indicator */}
      {isFailed && (
        <>
          <div className="w-4 h-0.5 bg-red-300" />
          <div className="w-2.5 h-2.5 rounded-full bg-red-500" title={task.status} />
        </>
      )}
    </div>
  );
}

/**
 * Main TaskTimeline component
 */
export function TaskTimeline({ task, className = '' }: TaskTimelineProps) {
  // Build timeline steps from task data
  const timelineSteps = useMemo(() => {
    const currentStatusIndex = getStatusIndex(task.status);
    const isFailed = task.status === 'failed';
    const isCancelled = task.status === 'cancelled';

    const steps: TimelineStep[] = [
      {
        status: 'pending',
        label: 'Created',
        timestamp: task.created_at,
        isActive: task.status === 'pending',
        isCompleted: currentStatusIndex > 0 || task.status === 'completed',
        isFailed: false,
        duration: null,
      },
      {
        status: 'queued',
        label: 'Queued',
        timestamp: currentStatusIndex >= 1 ? task.created_at : null, // Use created_at as approximation
        isActive: task.status === 'queued',
        isCompleted: currentStatusIndex > 1 || task.status === 'completed',
        isFailed: false,
        duration: null,
      },
      {
        status: 'assigned',
        label: 'Assigned to Worker',
        timestamp: currentStatusIndex >= 2 ? task.started_at : null,
        isActive: task.status === 'assigned',
        isCompleted: currentStatusIndex > 2 || task.status === 'completed',
        isFailed: false,
        duration: null,
      },
      {
        status: 'running',
        label: 'Running',
        timestamp: task.started_at,
        isActive: task.status === 'running',
        isCompleted: task.status === 'completed',
        isFailed: isFailed,
        duration: task.started_at
          ? calculateDuration(task.started_at, task.completed_at)
          : null,
      },
    ];

    // Add final status step
    if (isFailed) {
      steps.push({
        status: 'failed',
        label: 'Failed',
        timestamp: task.completed_at,
        isActive: false,
        isCompleted: false,
        isFailed: true,
        duration: null,
      });
    } else if (isCancelled) {
      steps.push({
        status: 'cancelled',
        label: 'Cancelled',
        timestamp: task.completed_at,
        isActive: false,
        isCompleted: false,
        isFailed: true,
        duration: null,
      });
    } else {
      steps.push({
        status: 'completed',
        label: 'Completed',
        timestamp: task.completed_at,
        isActive: false,
        isCompleted: task.status === 'completed',
        isFailed: false,
        duration: null,
      });
    }

    return steps;
  }, [task]);

  // Calculate total duration
  const totalDuration = useMemo(() => {
    if (task.completed_at) {
      return calculateDuration(task.created_at, task.completed_at);
    }
    if (task.status === 'running' || task.status === 'assigned') {
      return calculateDuration(task.created_at, null);
    }
    return null;
  }, [task]);

  return (
    <div className={className}>
      {/* Header with total duration */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-medium text-gray-700">Execution Timeline</h3>
        {totalDuration && (
          <span className="text-sm text-gray-500">
            Total: <span className="font-medium">{totalDuration}</span>
          </span>
        )}
      </div>

      {/* Timeline steps */}
      <div className="relative">
        {timelineSteps.map((step, index) => (
          <TimelineStep
            key={step.status}
            step={step}
            isLast={index === timelineSteps.length - 1}
          />
        ))}
      </div>

      {/* Error message if failed */}
      {task.error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-start gap-2">
            <svg
              className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800">Error Details</h4>
              <p className="text-sm text-red-700 mt-1">{task.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Progress bar for running tasks */}
      {task.status === 'running' && (
        <div className="mt-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Progress</span>
            <span>{task.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className="bg-blue-500 h-full rounded-full transition-all duration-300 animate-pulse"
              style={{ width: `${task.progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default TaskTimeline;
