/**
 * Dashboard Components Index
 *
 * Re-exports all dashboard components for easier imports.
 */

export {
  StatsCard,
  TaskIcon,
  WorkerIcon,
  WorkflowIcon,
  ActivityIcon,
  CheckIcon,
  ErrorIcon,
} from './StatsCard';
export type { StatsCardProps } from './StatsCard';

export { RecentTasks } from './RecentTasks';
export type { RecentTasksProps } from './RecentTasks';

export { WorkerGrid } from './WorkerGrid';
export type { WorkerGridProps } from './WorkerGrid';

export { ActiveWorkflows } from './ActiveWorkflows';
export type { ActiveWorkflowsProps } from './ActiveWorkflows';

export { SystemHealth, SystemHealthCompact } from './SystemHealth';
export type { SystemHealthProps } from './SystemHealth';
