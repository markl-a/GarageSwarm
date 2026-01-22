/**
 * Node Components Index
 *
 * Exports all custom node components for the workflow editor.
 */

export { BaseNode, createConditionHandles, createParallelHandles, createJoinHandles, createLoopHandles } from './BaseNode';
export { TaskNode } from './TaskNode';
export { ConditionNode } from './ConditionNode';
export { ParallelNode } from './ParallelNode';
export { JoinNode } from './JoinNode';
export { HumanReviewNode } from './HumanReviewNode';
export { LoopNode } from './LoopNode';

// Node types mapping for React Flow
import { TaskNode } from './TaskNode';
import { ConditionNode } from './ConditionNode';
import { ParallelNode } from './ParallelNode';
import { JoinNode } from './JoinNode';
import { HumanReviewNode } from './HumanReviewNode';
import { LoopNode } from './LoopNode';

export const nodeTypes = {
  task: TaskNode,
  condition: ConditionNode,
  parallel: ParallelNode,
  join: JoinNode,
  human_review: HumanReviewNode,
  loop: LoopNode,
} as const;
