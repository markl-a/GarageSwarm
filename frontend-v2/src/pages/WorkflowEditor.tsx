/**
 * WorkflowEditor - Main workflow editor page
 *
 * The primary interface for building and managing workflows with:
 * - React Flow canvas for visual workflow editing
 * - Left sidebar: Node palette (drag to add)
 * - Right sidebar: Property panel (edit selected node)
 * - Top toolbar: Save, Run, Template selector
 * - Bottom: Execution status viewer
 */

import React, { useCallback, useState, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { WorkflowCanvas, NodePalette, PropertyPanel, ExecutionViewer } from '@/components/workflow';
import { useWorkflowStore, useIsExecuting } from '@/stores/workflowStore';
import type { WorkflowDefinition, WorkflowTemplate } from '@/types/workflow';

// ============================================================================
// Icons
// ============================================================================

const SaveIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
  </svg>
);

const FolderOpenIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
  </svg>
);

const PlusIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
);

const UndoIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
  </svg>
);

const RedoIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
  </svg>
);

const TemplateIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
  </svg>
);

const SettingsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const ChevronDownIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

// ============================================================================
// Sample Templates (would normally come from API)
// ============================================================================

const SAMPLE_TEMPLATES: WorkflowTemplate[] = [
  {
    id: 'code-review',
    name: 'Code Review Pipeline',
    description: 'Automated code review with AI analysis and human approval',
    category: 'code',
    workflow: {
      name: 'Code Review Pipeline',
      description: 'Automated code review workflow',
      version: 1,
      nodes: [
        {
          id: 'node_1',
          type: 'task',
          position: { x: 250, y: 50 },
          data: {
            nodeType: 'task',
            label: 'Analyze Code',
            tool: 'claude_code',
            toolConfig: { toolId: 'claude_code', toolName: 'Claude Code', parameters: {} },
            prompt: 'Analyze the code changes and provide feedback',
            executionStatus: 'idle',
          },
        },
        {
          id: 'node_2',
          type: 'condition',
          position: { x: 250, y: 200 },
          data: {
            nodeType: 'condition',
            label: 'Has Issues?',
            conditionType: 'output',
            operator: 'contains',
            expectedOutput: 'issue',
            executionStatus: 'idle',
          },
        },
        {
          id: 'node_3',
          type: 'human_review',
          position: { x: 450, y: 350 },
          data: {
            nodeType: 'human_review',
            label: 'Human Review',
            reviewType: 'approval',
            instructions: 'Please review the AI analysis and approve or reject',
            executionStatus: 'idle',
          },
        },
        {
          id: 'node_4',
          type: 'task',
          position: { x: 100, y: 350 },
          data: {
            nodeType: 'task',
            label: 'Auto Approve',
            tool: 'shell',
            toolConfig: { toolId: 'shell', toolName: 'Shell Command', parameters: {} },
            prompt: 'Mark as approved',
            executionStatus: 'idle',
          },
        },
      ],
      edges: [
        { id: 'edge_1', source: 'node_1', target: 'node_2', type: 'smoothstep' },
        { id: 'edge_2', source: 'node_2', sourceHandle: 'true', target: 'node_3', type: 'smoothstep' },
        { id: 'edge_3', source: 'node_2', sourceHandle: 'false', target: 'node_4', type: 'smoothstep' },
      ],
      variables: {},
      metadata: { isTemplate: true },
    },
  },
  {
    id: 'parallel-analysis',
    name: 'Parallel Code Analysis',
    description: 'Run multiple AI tools in parallel for comprehensive analysis',
    category: 'analysis',
    workflow: {
      name: 'Parallel Code Analysis',
      description: 'Parallel analysis with multiple AI tools',
      version: 1,
      nodes: [
        {
          id: 'node_1',
          type: 'parallel',
          position: { x: 300, y: 50 },
          data: {
            nodeType: 'parallel',
            label: 'Split Analysis',
            waitForAll: true,
            executionStatus: 'idle',
          },
        },
        {
          id: 'node_2',
          type: 'task',
          position: { x: 100, y: 200 },
          data: {
            nodeType: 'task',
            label: 'Claude Analysis',
            tool: 'claude_code',
            toolConfig: { toolId: 'claude_code', toolName: 'Claude Code', parameters: {} },
            prompt: 'Analyze code quality and suggest improvements',
            executionStatus: 'idle',
          },
        },
        {
          id: 'node_3',
          type: 'task',
          position: { x: 300, y: 200 },
          data: {
            nodeType: 'task',
            label: 'Gemini Analysis',
            tool: 'gemini_cli',
            toolConfig: { toolId: 'gemini_cli', toolName: 'Gemini CLI', parameters: {} },
            prompt: 'Check for security vulnerabilities',
            executionStatus: 'idle',
          },
        },
        {
          id: 'node_4',
          type: 'task',
          position: { x: 500, y: 200 },
          data: {
            nodeType: 'task',
            label: 'Local LLM',
            tool: 'ollama',
            toolConfig: { toolId: 'ollama', toolName: 'Ollama', parameters: {} },
            prompt: 'Check code formatting and style',
            executionStatus: 'idle',
          },
        },
        {
          id: 'node_5',
          type: 'join',
          position: { x: 300, y: 350 },
          data: {
            nodeType: 'join',
            label: 'Merge Results',
            joinType: 'all',
            executionStatus: 'idle',
          },
        },
        {
          id: 'node_6',
          type: 'task',
          position: { x: 300, y: 500 },
          data: {
            nodeType: 'task',
            label: 'Generate Report',
            tool: 'claude_code',
            toolConfig: { toolId: 'claude_code', toolName: 'Claude Code', parameters: {} },
            prompt: 'Combine all analysis results into a comprehensive report',
            executionStatus: 'idle',
          },
        },
      ],
      edges: [
        { id: 'edge_1', source: 'node_1', sourceHandle: 'branch-1', target: 'node_2', type: 'smoothstep' },
        { id: 'edge_2', source: 'node_1', sourceHandle: 'branch-2', target: 'node_3', type: 'smoothstep' },
        { id: 'edge_3', source: 'node_1', sourceHandle: 'branch-3', target: 'node_4', type: 'smoothstep' },
        { id: 'edge_4', source: 'node_2', target: 'node_5', targetHandle: 'input-1', type: 'smoothstep' },
        { id: 'edge_5', source: 'node_3', target: 'node_5', targetHandle: 'input-2', type: 'smoothstep' },
        { id: 'edge_6', source: 'node_4', target: 'node_5', targetHandle: 'input-3', type: 'smoothstep' },
        { id: 'edge_7', source: 'node_5', target: 'node_6', type: 'smoothstep' },
      ],
      variables: {},
      metadata: { isTemplate: true },
    },
  },
];

// ============================================================================
// Toolbar Components
// ============================================================================

interface ToolbarButtonProps {
  onClick: () => void;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
  variant?: 'default' | 'primary' | 'danger';
}

const ToolbarButton: React.FC<ToolbarButtonProps> = ({
  onClick,
  disabled,
  title,
  children,
  variant = 'default',
}) => {
  const variantClasses = {
    default: 'text-gray-700 hover:bg-gray-100',
    primary: 'text-blue-600 hover:bg-blue-50',
    danger: 'text-red-600 hover:bg-red-50',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`
        flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg
        transition-colors disabled:opacity-50 disabled:cursor-not-allowed
        ${variantClasses[variant]}
      `}
    >
      {children}
    </button>
  );
};

interface TemplateDropdownProps {
  templates: WorkflowTemplate[];
  onSelect: (template: WorkflowTemplate) => void;
}

const TemplateDropdown: React.FC<TemplateDropdownProps> = ({ templates, onSelect }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
      >
        <TemplateIcon />
        Templates
        <ChevronDownIcon />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
            <div className="p-2">
              <p className="px-2 py-1 text-xs font-medium text-gray-500 uppercase">
                Choose a Template
              </p>
              {templates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => {
                    onSelect(template);
                    setIsOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <div className="font-medium text-sm text-gray-800">{template.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{template.description}</div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// ============================================================================
// Workflow Settings Modal
// ============================================================================

interface WorkflowSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const WorkflowSettingsModal: React.FC<WorkflowSettingsModalProps> = ({ isOpen, onClose }) => {
  const { workflowName, workflowDescription, setWorkflowName, setWorkflowDescription } = useWorkflowStore();
  const [name, setName] = useState(workflowName);
  const [description, setDescription] = useState(workflowDescription);

  useEffect(() => {
    setName(workflowName);
    setDescription(workflowDescription);
  }, [workflowName, workflowDescription, isOpen]);

  const handleSave = () => {
    setWorkflowName(name);
    setWorkflowDescription(description);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Workflow Settings</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Workflow name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Optional description"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Main WorkflowEditor Component
// ============================================================================

export const WorkflowEditor: React.FC = () => {
  const [showSettings, setShowSettings] = useState(false);
  const isExecuting = useIsExecuting();

  const {
    workflowName,
    isDirty,
    isPaletteOpen,
    isPropertyPanelOpen,
    isExecutionViewerOpen,
    togglePalette,
    togglePropertyPanel,
    toggleExecutionViewer,
    newWorkflow,
    saveWorkflow,
    loadWorkflow,
    undo,
    redo,
    canUndo,
    canRedo,
  } = useWorkflowStore();

  // Handle save
  const handleSave = useCallback(() => {
    const workflow = saveWorkflow();
    // In production, this would save to API
    console.log('Saving workflow:', workflow);
    // Show success notification
    alert('Workflow saved successfully!');
  }, [saveWorkflow]);

  // Handle load (mock file picker)
  const handleLoad = useCallback(() => {
    // In production, this would open a file picker or load from API
    const mockWorkflow: WorkflowDefinition = {
      id: 'loaded-workflow',
      name: 'Loaded Workflow',
      description: 'A workflow loaded from storage',
      version: 1,
      nodes: [],
      edges: [],
      variables: {},
      metadata: {},
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    loadWorkflow(mockWorkflow);
  }, [loadWorkflow]);

  // Handle template selection
  const handleTemplateSelect = useCallback((template: WorkflowTemplate) => {
    const workflow: WorkflowDefinition = {
      ...template.workflow,
      id: `workflow_${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    loadWorkflow(workflow);
  }, [loadWorkflow]);

  // Keyboard shortcuts for save
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        handleSave();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleSave]);

  return (
    <ReactFlowProvider>
      <div className="h-screen flex flex-col bg-gray-100">
        {/* Top Toolbar */}
        <header className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between shadow-sm z-40">
          {/* Left Section */}
          <div className="flex items-center gap-4">
            {/* Logo/Brand */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span className="font-semibold text-gray-800">GarageSwarm</span>
            </div>

            <div className="w-px h-6 bg-gray-300" />

            {/* Workflow Name */}
            <div className="flex items-center gap-2">
              <h1 className="font-medium text-gray-800">{workflowName}</h1>
              {isDirty && (
                <span className="text-xs text-orange-500 font-medium">(Unsaved)</span>
              )}
            </div>
          </div>

          {/* Center Section */}
          <div className="flex items-center gap-1">
            <ToolbarButton onClick={newWorkflow} title="New Workflow" disabled={isExecuting}>
              <PlusIcon />
              New
            </ToolbarButton>

            <ToolbarButton onClick={handleLoad} title="Open Workflow" disabled={isExecuting}>
              <FolderOpenIcon />
              Open
            </ToolbarButton>

            <ToolbarButton onClick={handleSave} title="Save Workflow (Ctrl+S)" variant="primary">
              <SaveIcon />
              Save
            </ToolbarButton>

            <div className="w-px h-6 bg-gray-300 mx-2" />

            <ToolbarButton onClick={undo} title="Undo (Ctrl+Z)" disabled={!canUndo() || isExecuting}>
              <UndoIcon />
            </ToolbarButton>

            <ToolbarButton onClick={redo} title="Redo (Ctrl+Shift+Z)" disabled={!canRedo() || isExecuting}>
              <RedoIcon />
            </ToolbarButton>

            <div className="w-px h-6 bg-gray-300 mx-2" />

            <TemplateDropdown templates={SAMPLE_TEMPLATES} onSelect={handleTemplateSelect} />
          </div>

          {/* Right Section */}
          <div className="flex items-center gap-2">
            <ToolbarButton onClick={() => setShowSettings(true)} title="Workflow Settings">
              <SettingsIcon />
            </ToolbarButton>
          </div>
        </header>

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden relative">
          {/* Left Sidebar - Node Palette */}
          <NodePalette isOpen={isPaletteOpen} onToggle={togglePalette} />

          {/* Center - Canvas */}
          <WorkflowCanvas />

          {/* Right Sidebar - Property Panel */}
          <PropertyPanel isOpen={isPropertyPanelOpen} onToggle={togglePropertyPanel} />
        </div>

        {/* Bottom - Execution Viewer */}
        <ExecutionViewer isOpen={isExecutionViewerOpen} onToggle={toggleExecutionViewer} />

        {/* Settings Modal */}
        <WorkflowSettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />
      </div>
    </ReactFlowProvider>
  );
};

export default WorkflowEditor;
