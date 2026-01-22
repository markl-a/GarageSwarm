/**
 * WorkflowCanvas - React Flow canvas component
 *
 * The main workflow editing canvas with custom node types, edge styles,
 * zoom controls, minimap, and drag-and-drop support.
 */

import React, { useCallback, useRef, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  useReactFlow,
  type ReactFlowInstance,
  type Connection,
  type XYPosition,
  ConnectionLineType,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { nodeTypes } from './nodes';
import type { WorkflowNode, WorkflowEdge, WorkflowNodeType, NodeExecutionStatus } from '@/types/workflow';
import { useWorkflowStore } from '@/stores/workflowStore';

// ============================================================================
// Custom Edge Styles
// ============================================================================

const edgeOptions = {
  type: 'smoothstep',
  animated: false,
  style: {
    strokeWidth: 2,
    stroke: '#9CA3AF',
  },
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 15,
    height: 15,
    color: '#9CA3AF',
  },
};

const connectionLineStyle = {
  strokeWidth: 2,
  stroke: '#3B82F6',
  strokeDasharray: '5 5',
};

// ============================================================================
// Minimap Node Colors
// ============================================================================

const getMinimapNodeColor = (node: WorkflowNode): string => {
  const statusColors: Record<NodeExecutionStatus, string> = {
    idle: '#E5E7EB',
    pending: '#FDE047',
    running: '#60A5FA',
    completed: '#4ADE80',
    failed: '#F87171',
    skipped: '#D1D5DB',
    waiting_approval: '#C084FC',
  };

  return statusColors[node.data.executionStatus] || '#E5E7EB';
};

// ============================================================================
// Keyboard Shortcuts Handler
// ============================================================================

const useKeyboardShortcuts = () => {
  const { undo, redo, canUndo, canRedo, deleteNode, selectedNodeId, duplicateNode } = useWorkflowStore();

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Prevent shortcuts when typing in inputs
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement
      ) {
        return;
      }

      // Undo: Ctrl/Cmd + Z
      if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !event.shiftKey) {
        event.preventDefault();
        if (canUndo()) undo();
        return;
      }

      // Redo: Ctrl/Cmd + Shift + Z or Ctrl/Cmd + Y
      if ((event.ctrlKey || event.metaKey) && (event.key === 'y' || (event.key === 'z' && event.shiftKey))) {
        event.preventDefault();
        if (canRedo()) redo();
        return;
      }

      // Delete: Delete or Backspace
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedNodeId) {
        event.preventDefault();
        deleteNode(selectedNodeId);
        return;
      }

      // Duplicate: Ctrl/Cmd + D
      if ((event.ctrlKey || event.metaKey) && event.key === 'd' && selectedNodeId) {
        event.preventDefault();
        duplicateNode(selectedNodeId);
        return;
      }
    },
    [undo, redo, canUndo, canRedo, deleteNode, selectedNodeId, duplicateNode]
  );

  React.useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
};

// ============================================================================
// Zoom Level Display Component
// ============================================================================

const ZoomDisplay: React.FC<{ zoom: number }> = ({ zoom }) => (
  <div className="px-2 py-1 bg-white rounded shadow-sm text-xs text-gray-600 font-mono">
    {Math.round(zoom * 100)}%
  </div>
);

// ============================================================================
// WorkflowCanvas Component
// ============================================================================

interface WorkflowCanvasProps {
  className?: string;
}

export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({ className = '' }) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [zoom, setZoom] = useState(1);

  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    selectNode,
    selectEdge,
    clearSelection,
    setZoomLevel,
    setCanvasPosition,
  } = useWorkflowStore();

  // Enable keyboard shortcuts
  useKeyboardShortcuts();

  // Handle node selection
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: WorkflowNode) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  // Handle edge selection
  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: WorkflowEdge) => {
      selectEdge(edge.id);
    },
    [selectEdge]
  );

  // Handle pane click (deselect)
  const handlePaneClick = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  // Handle drag over for drop zone
  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle drop to create new node
  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow') as WorkflowNodeType;
      if (!type || !reactFlowInstance || !reactFlowWrapper.current) {
        return;
      }

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      addNode(type, position);
    },
    [reactFlowInstance, addNode]
  );

  // Handle viewport changes
  const handleMoveEnd = useCallback(
    (_event: React.MouseEvent | React.TouchEvent | null, viewport: { x: number; y: number; zoom: number }) => {
      setZoomLevel(viewport.zoom);
      setCanvasPosition({ x: viewport.x, y: viewport.y });
      setZoom(viewport.zoom);
    },
    [setZoomLevel, setCanvasPosition]
  );

  // Connection validation
  const isValidConnection = useCallback((connection: Connection) => {
    // Prevent self-connections
    if (connection.source === connection.target) {
      return false;
    }
    return true;
  }, []);

  // Memoized props for React Flow
  const defaultEdgeOptions = useMemo(() => edgeOptions, []);

  return (
    <div ref={reactFlowWrapper} className={`flex-1 h-full ${className}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={handlePaneClick}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onMoveEnd={handleMoveEnd}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineType={ConnectionLineType.SmoothStep}
        connectionLineStyle={connectionLineStyle}
        isValidConnection={isValidConnection}
        fitView
        fitViewOptions={{
          padding: 0.2,
          minZoom: 0.5,
          maxZoom: 1.5,
        }}
        minZoom={0.1}
        maxZoom={2}
        snapToGrid
        snapGrid={[16, 16]}
        deleteKeyCode={['Backspace', 'Delete']}
        selectionKeyCode={['Shift']}
        multiSelectionKeyCode={['Control', 'Meta']}
        panOnScroll
        panOnScrollSpeed={0.8}
        zoomOnDoubleClick
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        {/* Background Grid */}
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1}
          color="#E5E7EB"
        />

        {/* Zoom Controls */}
        <Controls
          showInteractive={false}
          className="!bg-white !rounded-lg !shadow-lg !border !border-gray-200"
        />

        {/* Minimap */}
        <MiniMap
          nodeColor={getMinimapNodeColor}
          nodeStrokeWidth={3}
          zoomable
          pannable
          className="!bg-white !rounded-lg !shadow-lg !border !border-gray-200"
          style={{
            width: 150,
            height: 100,
          }}
        />

        {/* Top-Left Panel: Zoom Display */}
        <Panel position="top-left" className="!m-4">
          <ZoomDisplay zoom={zoom} />
        </Panel>

        {/* Bottom Panel: Instructions */}
        <Panel position="bottom-center" className="!mb-4">
          <div className="px-4 py-2 bg-white/90 backdrop-blur-sm rounded-lg shadow-sm text-xs text-gray-500 flex items-center gap-4">
            <span>
              <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-700">Scroll</kbd> to pan
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-700">Ctrl</kbd> + <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-700">Scroll</kbd> to zoom
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-700">Delete</kbd> to remove
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-700">Ctrl+Z</kbd> undo
            </span>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

export default WorkflowCanvas;
