/**
 * Workflow Store - Zustand store for workflow state management
 *
 * Manages the workflow editor state including nodes, edges, selection,
 * execution state, and undo/redo history.
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type Connection,
  type NodeChange,
  type EdgeChange,
} from '@xyflow/react';
import type {
  WorkflowNode,
  WorkflowEdge,
  WorkflowDefinition,
  WorkflowExecution,
  WorkflowNodeData,
  WorkflowNodeType,
  NodeExecutionLog,
  NodeExecutionStatus,
  WorkflowExecutionStatus,
} from '@/types/workflow';
import { createDefaultNodeData } from '@/types/workflow';

// ============================================================================
// History Types
// ============================================================================

interface HistoryState {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

// ============================================================================
// Store State Interface
// ============================================================================

interface WorkflowState {
  // Workflow Definition
  workflowId: string | null;
  workflowName: string;
  workflowDescription: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables: Record<string, unknown>;
  isDirty: boolean;

  // Selection
  selectedNodeId: string | null;
  selectedEdgeId: string | null;

  // Execution State
  execution: WorkflowExecution | null;
  isExecuting: boolean;
  executionLogs: NodeExecutionLog[];

  // UI State
  isPaletteOpen: boolean;
  isPropertyPanelOpen: boolean;
  isExecutionViewerOpen: boolean;
  zoomLevel: number;
  canvasPosition: { x: number; y: number };

  // History for Undo/Redo
  history: HistoryState[];
  historyIndex: number;
  maxHistorySize: number;

  // Templates
  availableTemplates: WorkflowDefinition[];
}

// ============================================================================
// Store Actions Interface
// ============================================================================

interface WorkflowActions {
  // Node Operations
  onNodesChange: (changes: NodeChange<WorkflowNode>[]) => void;
  addNode: (type: WorkflowNodeType, position: { x: number; y: number }) => string;
  updateNode: (nodeId: string, data: Partial<WorkflowNodeData>) => void;
  deleteNode: (nodeId: string) => void;
  duplicateNode: (nodeId: string) => void;

  // Edge Operations
  onEdgesChange: (changes: EdgeChange<WorkflowEdge>[]) => void;
  onConnect: (connection: Connection) => void;
  updateEdge: (edgeId: string, data: Partial<WorkflowEdge>) => void;
  deleteEdge: (edgeId: string) => void;

  // Selection
  selectNode: (nodeId: string | null) => void;
  selectEdge: (edgeId: string | null) => void;
  clearSelection: () => void;

  // Workflow Operations
  loadWorkflow: (workflow: WorkflowDefinition) => void;
  saveWorkflow: () => WorkflowDefinition;
  newWorkflow: () => void;
  setWorkflowName: (name: string) => void;
  setWorkflowDescription: (description: string) => void;

  // Execution Operations
  startExecution: () => void;
  pauseExecution: () => void;
  resumeExecution: () => void;
  stopExecution: () => void;
  updateNodeExecutionStatus: (nodeId: string, status: NodeExecutionStatus, error?: string) => void;
  setExecutionStatus: (status: WorkflowExecutionStatus) => void;
  addExecutionLog: (log: NodeExecutionLog) => void;
  clearExecutionLogs: () => void;

  // UI Operations
  togglePalette: () => void;
  togglePropertyPanel: () => void;
  toggleExecutionViewer: () => void;
  setZoomLevel: (level: number) => void;
  setCanvasPosition: (position: { x: number; y: number }) => void;

  // History Operations
  undo: () => void;
  redo: () => void;
  pushHistory: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;

  // Variable Operations
  setVariable: (key: string, value: unknown) => void;
  deleteVariable: (key: string) => void;

  // Template Operations
  loadTemplate: (templateId: string) => void;
  setAvailableTemplates: (templates: WorkflowDefinition[]) => void;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: WorkflowState = {
  workflowId: null,
  workflowName: 'Untitled Workflow',
  workflowDescription: '',
  nodes: [],
  edges: [],
  variables: {},
  isDirty: false,

  selectedNodeId: null,
  selectedEdgeId: null,

  execution: null,
  isExecuting: false,
  executionLogs: [],

  isPaletteOpen: true,
  isPropertyPanelOpen: true,
  isExecutionViewerOpen: false,
  zoomLevel: 1,
  canvasPosition: { x: 0, y: 0 },

  history: [],
  historyIndex: -1,
  maxHistorySize: 50,

  availableTemplates: [],
};

// ============================================================================
// Helper Functions
// ============================================================================

function generateNodeId(): string {
  return `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function generateEdgeId(): string {
  return `edge_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// ============================================================================
// Store Creation
// ============================================================================

export const useWorkflowStore = create<WorkflowState & WorkflowActions>()(
  devtools(
    subscribeWithSelector(
      immer((set, get) => ({
        ...initialState,

        // ====================================================================
        // Node Operations
        // ====================================================================

        onNodesChange: (changes) => {
          set((state) => {
            state.nodes = applyNodeChanges(changes, state.nodes) as WorkflowNode[];
            state.isDirty = true;
          });
        },

        addNode: (type, position) => {
          const nodeId = generateNodeId();
          const defaultData = createDefaultNodeData(type);

          set((state) => {
            state.nodes.push({
              id: nodeId,
              type,
              position,
              data: defaultData,
            });
            state.isDirty = true;
            state.selectedNodeId = nodeId;
          });

          get().pushHistory();
          return nodeId;
        },

        updateNode: (nodeId, data) => {
          set((state) => {
            const node = state.nodes.find((n) => n.id === nodeId);
            if (node) {
              node.data = { ...node.data, ...data } as WorkflowNodeData;
              state.isDirty = true;
            }
          });
          get().pushHistory();
        },

        deleteNode: (nodeId) => {
          set((state) => {
            state.nodes = state.nodes.filter((n) => n.id !== nodeId);
            state.edges = state.edges.filter(
              (e) => e.source !== nodeId && e.target !== nodeId
            );
            if (state.selectedNodeId === nodeId) {
              state.selectedNodeId = null;
            }
            state.isDirty = true;
          });
          get().pushHistory();
        },

        duplicateNode: (nodeId) => {
          const state = get();
          const node = state.nodes.find((n) => n.id === nodeId);
          if (!node) return;

          const newNodeId = generateNodeId();
          set((state) => {
            state.nodes.push({
              ...node,
              id: newNodeId,
              position: {
                x: node.position.x + 50,
                y: node.position.y + 50,
              },
              data: {
                ...node.data,
                label: `${node.data.label} (Copy)`,
                executionStatus: 'idle',
              },
            } as WorkflowNode);
            state.isDirty = true;
            state.selectedNodeId = newNodeId;
          });
          get().pushHistory();
        },

        // ====================================================================
        // Edge Operations
        // ====================================================================

        onEdgesChange: (changes) => {
          set((state) => {
            state.edges = applyEdgeChanges(changes, state.edges) as WorkflowEdge[];
            state.isDirty = true;
          });
        },

        onConnect: (connection) => {
          set((state) => {
            const newEdge: WorkflowEdge = {
              id: generateEdgeId(),
              source: connection.source!,
              target: connection.target!,
              sourceHandle: connection.sourceHandle,
              targetHandle: connection.targetHandle,
              type: 'smoothstep',
              animated: false,
              data: {},
            };
            state.edges = addEdge(newEdge, state.edges) as WorkflowEdge[];
            state.isDirty = true;
          });
          get().pushHistory();
        },

        updateEdge: (edgeId, data) => {
          set((state) => {
            const edge = state.edges.find((e) => e.id === edgeId);
            if (edge) {
              Object.assign(edge, data);
              state.isDirty = true;
            }
          });
          get().pushHistory();
        },

        deleteEdge: (edgeId) => {
          set((state) => {
            state.edges = state.edges.filter((e) => e.id !== edgeId);
            if (state.selectedEdgeId === edgeId) {
              state.selectedEdgeId = null;
            }
            state.isDirty = true;
          });
          get().pushHistory();
        },

        // ====================================================================
        // Selection
        // ====================================================================

        selectNode: (nodeId) => {
          set((state) => {
            state.selectedNodeId = nodeId;
            state.selectedEdgeId = null;
            if (nodeId) {
              state.isPropertyPanelOpen = true;
            }
          });
        },

        selectEdge: (edgeId) => {
          set((state) => {
            state.selectedEdgeId = edgeId;
            state.selectedNodeId = null;
          });
        },

        clearSelection: () => {
          set((state) => {
            state.selectedNodeId = null;
            state.selectedEdgeId = null;
          });
        },

        // ====================================================================
        // Workflow Operations
        // ====================================================================

        loadWorkflow: (workflow) => {
          set((state) => {
            state.workflowId = workflow.id;
            state.workflowName = workflow.name;
            state.workflowDescription = workflow.description || '';
            state.nodes = workflow.nodes;
            state.edges = workflow.edges;
            state.variables = workflow.variables || {};
            state.isDirty = false;
            state.selectedNodeId = null;
            state.selectedEdgeId = null;
            state.history = [];
            state.historyIndex = -1;
          });
          get().pushHistory();
        },

        saveWorkflow: () => {
          const state = get();
          const now = new Date().toISOString();

          const workflow: WorkflowDefinition = {
            id: state.workflowId || generateNodeId(),
            name: state.workflowName,
            description: state.workflowDescription,
            version: 1,
            nodes: state.nodes,
            edges: state.edges,
            variables: state.variables,
            metadata: {},
            createdAt: now,
            updatedAt: now,
          };

          set((state) => {
            state.workflowId = workflow.id;
            state.isDirty = false;
          });

          return workflow;
        },

        newWorkflow: () => {
          set((state) => {
            Object.assign(state, {
              ...initialState,
              isPaletteOpen: state.isPaletteOpen,
              isPropertyPanelOpen: state.isPropertyPanelOpen,
              availableTemplates: state.availableTemplates,
            });
          });
        },

        setWorkflowName: (name) => {
          set((state) => {
            state.workflowName = name;
            state.isDirty = true;
          });
        },

        setWorkflowDescription: (description) => {
          set((state) => {
            state.workflowDescription = description;
            state.isDirty = true;
          });
        },

        // ====================================================================
        // Execution Operations
        // ====================================================================

        startExecution: () => {
          const state = get();
          const now = new Date().toISOString();

          set((state) => {
            state.isExecuting = true;
            state.execution = {
              id: generateNodeId(),
              workflowId: state.workflowId || '',
              status: 'running',
              startTime: now,
              executedNodes: [],
              nodeStatuses: {},
              nodeOutputs: {},
              logs: [],
              variables: { ...state.variables },
            };
            state.isExecutionViewerOpen = true;

            // Reset all node execution statuses
            state.nodes.forEach((node) => {
              node.data.executionStatus = 'pending';
              node.data.executionError = undefined;
            });
          });
        },

        pauseExecution: () => {
          set((state) => {
            if (state.execution) {
              state.execution.status = 'paused';
            }
          });
        },

        resumeExecution: () => {
          set((state) => {
            if (state.execution) {
              state.execution.status = 'running';
            }
          });
        },

        stopExecution: () => {
          set((state) => {
            if (state.execution) {
              state.execution.status = 'cancelled';
              state.execution.endTime = new Date().toISOString();
            }
            state.isExecuting = false;
          });
        },

        updateNodeExecutionStatus: (nodeId, status, error) => {
          set((state) => {
            const node = state.nodes.find((n) => n.id === nodeId);
            if (node) {
              node.data.executionStatus = status;
              if (error) {
                node.data.executionError = error;
              }
              if (status === 'running') {
                node.data.executionStartTime = new Date().toISOString();
                if (state.execution) {
                  state.execution.currentNodeId = nodeId;
                }
              }
              if (status === 'completed' || status === 'failed') {
                node.data.executionEndTime = new Date().toISOString();
                if (state.execution) {
                  state.execution.executedNodes.push(nodeId);
                  state.execution.nodeStatuses[nodeId] = status;
                }
              }
            }
          });
        },

        setExecutionStatus: (status) => {
          set((state) => {
            if (state.execution) {
              state.execution.status = status;
              if (status === 'completed' || status === 'failed' || status === 'cancelled') {
                state.execution.endTime = new Date().toISOString();
                state.isExecuting = false;
              }
            }
          });
        },

        addExecutionLog: (log) => {
          set((state) => {
            state.executionLogs.push(log);
            if (state.execution) {
              state.execution.logs.push(log);
            }
          });
        },

        clearExecutionLogs: () => {
          set((state) => {
            state.executionLogs = [];
          });
        },

        // ====================================================================
        // UI Operations
        // ====================================================================

        togglePalette: () => {
          set((state) => {
            state.isPaletteOpen = !state.isPaletteOpen;
          });
        },

        togglePropertyPanel: () => {
          set((state) => {
            state.isPropertyPanelOpen = !state.isPropertyPanelOpen;
          });
        },

        toggleExecutionViewer: () => {
          set((state) => {
            state.isExecutionViewerOpen = !state.isExecutionViewerOpen;
          });
        },

        setZoomLevel: (level) => {
          set((state) => {
            state.zoomLevel = level;
          });
        },

        setCanvasPosition: (position) => {
          set((state) => {
            state.canvasPosition = position;
          });
        },

        // ====================================================================
        // History Operations
        // ====================================================================

        pushHistory: () => {
          set((state) => {
            const currentState: HistoryState = {
              nodes: JSON.parse(JSON.stringify(state.nodes)),
              edges: JSON.parse(JSON.stringify(state.edges)),
            };

            // Remove any redo states
            state.history = state.history.slice(0, state.historyIndex + 1);

            // Add new state
            state.history.push(currentState);

            // Limit history size
            if (state.history.length > state.maxHistorySize) {
              state.history = state.history.slice(-state.maxHistorySize);
            }

            state.historyIndex = state.history.length - 1;
          });
        },

        undo: () => {
          const state = get();
          if (state.historyIndex > 0) {
            set((state) => {
              state.historyIndex--;
              const historyState = state.history[state.historyIndex];
              state.nodes = JSON.parse(JSON.stringify(historyState.nodes));
              state.edges = JSON.parse(JSON.stringify(historyState.edges));
              state.isDirty = true;
            });
          }
        },

        redo: () => {
          const state = get();
          if (state.historyIndex < state.history.length - 1) {
            set((state) => {
              state.historyIndex++;
              const historyState = state.history[state.historyIndex];
              state.nodes = JSON.parse(JSON.stringify(historyState.nodes));
              state.edges = JSON.parse(JSON.stringify(historyState.edges));
              state.isDirty = true;
            });
          }
        },

        canUndo: () => {
          return get().historyIndex > 0;
        },

        canRedo: () => {
          const state = get();
          return state.historyIndex < state.history.length - 1;
        },

        // ====================================================================
        // Variable Operations
        // ====================================================================

        setVariable: (key, value) => {
          set((state) => {
            state.variables[key] = value;
            state.isDirty = true;
          });
        },

        deleteVariable: (key) => {
          set((state) => {
            delete state.variables[key];
            state.isDirty = true;
          });
        },

        // ====================================================================
        // Template Operations
        // ====================================================================

        loadTemplate: (templateId) => {
          const template = get().availableTemplates.find((t) => t.id === templateId);
          if (template) {
            get().loadWorkflow(template);
          }
        },

        setAvailableTemplates: (templates) => {
          set((state) => {
            state.availableTemplates = templates;
          });
        },
      }))
    ),
    { name: 'workflow-store' }
  )
);

// ============================================================================
// Selector Hooks
// ============================================================================

export const useSelectedNode = () => {
  return useWorkflowStore((state) => {
    if (!state.selectedNodeId) return null;
    return state.nodes.find((n) => n.id === state.selectedNodeId) || null;
  });
};

export const useSelectedEdge = () => {
  return useWorkflowStore((state) => {
    if (!state.selectedEdgeId) return null;
    return state.edges.find((e) => e.id === state.selectedEdgeId) || null;
  });
};

export const useIsExecuting = () => {
  return useWorkflowStore((state) => state.isExecuting);
};

export const useExecutionStatus = () => {
  return useWorkflowStore((state) => state.execution?.status || 'idle');
};

export const useNodeExecutionStatus = (nodeId: string) => {
  return useWorkflowStore((state) => {
    const node = state.nodes.find((n) => n.id === nodeId);
    return node?.data.executionStatus || 'idle';
  });
};
