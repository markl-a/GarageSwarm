/**
 * TaskStatusBadge Component
 *
 * Displays a styled badge for task status with optional pulse animation for running tasks.
 */

import React from 'react';
import type { TaskStatus } from '../../types/task';
import { getStatusConfig } from '../../types/task';

interface TaskStatusBadgeProps {
  status: TaskStatus;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

/**
 * Get status icon based on status type
 */
function StatusIcon({ status, className }: { status: TaskStatus; className?: string }) {
  const iconClass = `w-4 h-4 ${className || ''}`;

  switch (status) {
    case 'pending':
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case 'queued':
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      );
    case 'assigned':
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      );
    case 'running':
      return (
        <svg className={`${iconClass} animate-spin`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      );
    case 'completed':
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case 'failed':
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case 'cancelled':
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
        </svg>
      );
    default:
      return null;
  }
}

/**
 * TaskStatusBadge component
 */
export function TaskStatusBadge({
  status,
  size = 'md',
  showIcon = true,
  className = '',
}: TaskStatusBadgeProps) {
  const config = getStatusConfig(status);

  // Size classes
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  const iconSizeClasses = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 font-medium rounded-full border
        ${config.bgColor} ${config.color} ${config.borderColor}
        ${sizeClasses[size]}
        ${config.pulseAnimation ? 'animate-pulse' : ''}
        ${className}
      `}
    >
      {showIcon && <StatusIcon status={status} className={iconSizeClasses[size]} />}
      {config.label}
    </span>
  );
}

/**
 * Mini status dot for compact displays
 */
export function TaskStatusDot({
  status,
  size = 'md',
  className = '',
}: {
  status: TaskStatus;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const config = getStatusConfig(status);

  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4',
  };

  // Get the dot color based on status
  const dotColors: Record<TaskStatus, string> = {
    pending: 'bg-yellow-500',
    queued: 'bg-orange-500',
    assigned: 'bg-purple-500',
    running: 'bg-blue-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    cancelled: 'bg-gray-500',
  };

  return (
    <span
      className={`
        inline-block rounded-full
        ${dotColors[status]}
        ${sizeClasses[size]}
        ${config.pulseAnimation ? 'animate-pulse' : ''}
        ${className}
      `}
      title={config.label}
    />
  );
}

/**
 * Progress indicator for running tasks
 */
export function TaskProgressIndicator({
  status,
  progress,
  className = '',
}: {
  status: TaskStatus;
  progress: number;
  className?: string;
}) {
  const isRunning = status === 'running';

  if (!isRunning && progress === 0) {
    return null;
  }

  return (
    <div className={`w-full ${className}`}>
      <div className="flex justify-between items-center mb-1">
        <TaskStatusBadge status={status} size="sm" />
        <span className="text-xs text-gray-500">{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`
            h-full rounded-full transition-all duration-300
            ${isRunning ? 'bg-blue-500 animate-pulse' : 'bg-green-500'}
          `}
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
    </div>
  );
}

export default TaskStatusBadge;
