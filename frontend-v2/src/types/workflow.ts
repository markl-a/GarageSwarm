/**
 * Workflow Types for GarageSwarm
 *
 * These types define the structure of workflow nodes, edges, and execution state.
 */

import type { Node, Edge } from '@xyflow/react';

// ============================================================================
// Node Types
// ============================================================================

export type WorkflowNodeType =
  | 'task'
  | 'condition'
  | 'parallel'
  | 'join'
  | 'human_review'
  | 'loop';

export type NodeExecutionStatus =
  | 'idle'
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'waiting_approval';

// ============================================================================
// Tool Configuration
// ============================================================================

export interface ToolConfig {
  toolId: string;
  toolName: string;
  parameters: Record<string, unknown>;
}

export const AVAILABLE_TOOLS = [
  { id: 'claude_code', name: 'Claude Code', icon: 'terminal' },
  { id: 'gemini_cli', name: 'Gemini CLI', icon: 'sparkles' },
  { id: 'ollama', name: 'Ollama', icon: 'cpu' },
  { id: 'shell', name: 'Shell Command', icon: 'command-line' },
  { id: 'http', name: 'HTTP Request', icon: 'globe' },
  { id: 'file', name: 'File Operation', icon: 'folder' },
] as const;

export type ToolId = typeof AVAILABLE_TOOLS[number]['id'];

// ============================================================================
// Node Data Types
// ============================================================================

export interface BaseNodeData {
  label: string;
  description?: string;
  executionStatus: NodeExecutionStatus;
  executionError?: string;
  executionDuration?: number;
  executionStartTime?: string;
  executionEndTime?: string;
}

export interface TaskNodeData extends BaseNodeData {
  nodeType: 'task';
  tool: ToolId;
  toolConfig: ToolConfig;
  prompt: string;
  timeout?: number;
  retryCount?: number;
  retryDelay?: number;
  workerId?: string;
  outputVariable?: string;
}

export interface ConditionNodeData extends BaseNodeData {
  nodeType: 'condition';
  conditionType: 'expression' | 'status' | 'output';
  expression?: string;
  sourceNodeId?: string;
  expectedStatus?: NodeExecutionStatus;
  expectedOutput?: string;
  operator?: 'equals' | 'contains' | 'regex' | 'greater' | 'less';
}

export interface ParallelNodeData extends BaseNodeData {
  nodeType: 'parallel';
  maxConcurrency?: number;
  waitForAll: boolean;
}

export interface JoinNodeData extends BaseNodeData {
  nodeType: 'join';
  joinType: 'all' | 'any' | 'n_of_m';
  minRequired?: number;
  timeout?: number;
}

export interface HumanReviewNodeData extends BaseNodeData {
  nodeType: 'human_review';
  reviewType: 'approval' | 'input' | 'choice';
  instructions: string;
  choices?: string[];
  timeoutAction?: 'approve' | 'reject' | 'skip';
  timeoutMinutes?: number;
  assigneeId?: string;
  assigneeEmail?: string;
}

export interface LoopNodeData extends BaseNodeData {
  nodeType: 'loop';
  loopType: 'count' | 'while' | 'for_each';
  maxIterations: number;
  currentIteration?: number;
  countValue?: number;
  whileCondition?: string;
  forEachSource?: string;
  forEachVariable?: string;
}

export type WorkflowNodeData =
  | TaskNodeData
  | ConditionNodeData
  | ParallelNodeData
  | JoinNodeData
  | HumanReviewNodeData
  | LoopNodeData;

// ============================================================================
// Node Type Guards
// ============================================================================

export function isTaskNodeData(data: WorkflowNodeData): data is TaskNodeData {
  return data.nodeType === 'task';
}

export function isConditionNodeData(data: WorkflowNodeData): data is ConditionNodeData {
  return data.nodeType === 'condition';
}

export function isParallelNodeData(data: WorkflowNodeData): data is ParallelNodeData {
  return data.nodeType === 'parallel';
}

export function isJoinNodeData(data: WorkflowNodeData): data is JoinNodeData {
  return data.nodeType === 'join';
}

export function isHumanReviewNodeData(data: WorkflowNodeData): data is HumanReviewNodeData {
  return data.nodeType === 'human_review';
}

export function isLoopNodeData(data: WorkflowNodeData): data is LoopNodeData {
  return data.nodeType === 'loop';
}

// ============================================================================
// React Flow Node Types
// ============================================================================

export type WorkflowNode = Node<WorkflowNodeData, WorkflowNodeType>;

// ============================================================================
// Edge Types
// ============================================================================

export interface WorkflowEdgeData {
  label?: string;
  conditionBranch?: 'true' | 'false';
  animated?: boolean;
}

export type WorkflowEdge = Edge<WorkflowEdgeData>;

// ============================================================================
// Workflow Definition
// ============================================================================

export interface WorkflowDefinition {
  id: string;
  name: string;
  description?: string;
  version: number;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables: Record<string, unknown>;
  metadata: WorkflowMetadata;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowMetadata {
  author?: string;
  tags?: string[];
  category?: string;
  isTemplate?: boolean;
  templateId?: string;
}

// ============================================================================
// Workflow Execution
// ============================================================================

export type WorkflowExecutionStatus =
  | 'idle'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface NodeExecutionLog {
  nodeId: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  data?: Record<string, unknown>;
}

export interface WorkflowExecution {
  id: string;
  workflowId: string;
  status: WorkflowExecutionStatus;
  startTime: string;
  endTime?: string;
  currentNodeId?: string;
  executedNodes: string[];
  nodeStatuses: Record<string, NodeExecutionStatus>;
  nodeOutputs: Record<string, unknown>;
  logs: NodeExecutionLog[];
  error?: string;
  variables: Record<string, unknown>;
}

// ============================================================================
// Workflow Templates
// ============================================================================

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  thumbnail?: string;
  workflow: Omit<WorkflowDefinition, 'id' | 'createdAt' | 'updatedAt'>;
}

export const WORKFLOW_CATEGORIES = [
  { id: 'code', name: 'Code Generation', icon: 'code' },
  { id: 'analysis', name: 'Code Analysis', icon: 'search' },
  { id: 'testing', name: 'Testing', icon: 'check' },
  { id: 'deployment', name: 'Deployment', icon: 'rocket' },
  { id: 'documentation', name: 'Documentation', icon: 'book' },
  { id: 'custom', name: 'Custom', icon: 'puzzle' },
] as const;

// ============================================================================
// Node Palette Configuration
// ============================================================================

export interface NodePaletteItem {
  type: WorkflowNodeType;
  label: string;
  description: string;
  icon: string;
  category: string;
  defaultData: Partial<WorkflowNodeData>;
}

export const NODE_PALETTE_ITEMS: NodePaletteItem[] = [
  {
    type: 'task',
    label: 'Task',
    description: 'Execute a task with an AI tool',
    icon: 'play',
    category: 'Execution',
    defaultData: {
      nodeType: 'task',
      label: 'New Task',
      tool: 'claude_code',
      toolConfig: { toolId: 'claude_code', toolName: 'Claude Code', parameters: {} },
      prompt: '',
      executionStatus: 'idle',
    },
  },
  {
    type: 'condition',
    label: 'Condition',
    description: 'Branch based on a condition',
    icon: 'git-branch',
    category: 'Control Flow',
    defaultData: {
      nodeType: 'condition',
      label: 'Condition',
      conditionType: 'expression',
      expression: '',
      executionStatus: 'idle',
    },
  },
  {
    type: 'parallel',
    label: 'Parallel',
    description: 'Split into parallel branches',
    icon: 'git-fork',
    category: 'Control Flow',
    defaultData: {
      nodeType: 'parallel',
      label: 'Parallel',
      waitForAll: true,
      executionStatus: 'idle',
    },
  },
  {
    type: 'join',
    label: 'Join',
    description: 'Merge parallel branches',
    icon: 'git-merge',
    category: 'Control Flow',
    defaultData: {
      nodeType: 'join',
      label: 'Join',
      joinType: 'all',
      executionStatus: 'idle',
    },
  },
  {
    type: 'human_review',
    label: 'Human Review',
    description: 'Wait for human approval or input',
    icon: 'user-check',
    category: 'Human',
    defaultData: {
      nodeType: 'human_review',
      label: 'Human Review',
      reviewType: 'approval',
      instructions: '',
      executionStatus: 'idle',
    },
  },
  {
    type: 'loop',
    label: 'Loop',
    description: 'Repeat a section of the workflow',
    icon: 'repeat',
    category: 'Control Flow',
    defaultData: {
      nodeType: 'loop',
      label: 'Loop',
      loopType: 'count',
      maxIterations: 10,
      countValue: 3,
      executionStatus: 'idle',
    },
  },
];

// ============================================================================
// Helper Functions
// ============================================================================

export function getNodePaletteItem(type: WorkflowNodeType): NodePaletteItem | undefined {
  return NODE_PALETTE_ITEMS.find(item => item.type === type);
}

export function createDefaultNodeData(type: WorkflowNodeType): WorkflowNodeData {
  const item = getNodePaletteItem(type);
  if (!item) {
    throw new Error(`Unknown node type: ${type}`);
  }
  return item.defaultData as WorkflowNodeData;
}

export function getStatusColor(status: NodeExecutionStatus): string {
  const colors: Record<NodeExecutionStatus, string> = {
    idle: 'gray',
    pending: 'yellow',
    running: 'blue',
    completed: 'green',
    failed: 'red',
    skipped: 'gray',
    waiting_approval: 'purple',
  };
  return colors[status];
}

export function getStatusLabel(status: NodeExecutionStatus): string {
  const labels: Record<NodeExecutionStatus, string> = {
    idle: 'Idle',
    pending: 'Pending',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    skipped: 'Skipped',
    waiting_approval: 'Waiting Approval',
  };
  return labels[status];
}
