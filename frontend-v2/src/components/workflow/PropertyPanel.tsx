/**
 * PropertyPanel - Node property editor component
 *
 * Displays a dynamic form for editing the selected node's properties
 * based on its type (task, condition, parallel, join, human_review, loop).
 */

import React, { useState, useCallback, useEffect } from 'react';
import type {
  WorkflowNode,
  WorkflowNodeData,
  TaskNodeData,
  ConditionNodeData,
  ParallelNodeData,
  JoinNodeData,
  HumanReviewNodeData,
  LoopNodeData,
  ToolId,
} from '@/types/workflow';
import {
  AVAILABLE_TOOLS,
  isTaskNodeData,
  isConditionNodeData,
  isParallelNodeData,
  isJoinNodeData,
  isHumanReviewNodeData,
  isLoopNodeData,
} from '@/types/workflow';
import { useWorkflowStore, useSelectedNode } from '@/stores/workflowStore';

// ============================================================================
// Icons
// ============================================================================

const CloseIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const TrashIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

const DuplicateIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

// ============================================================================
// Types
// ============================================================================

interface PropertyPanelProps {
  isOpen: boolean;
  onToggle: () => void;
}

// ============================================================================
// Form Input Components
// ============================================================================

interface TextInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

const TextInput: React.FC<TextInputProps> = ({ label, value, onChange, placeholder, disabled }) => (
  <div className="space-y-1">
    <label className="block text-sm font-medium text-gray-700">{label}</label>
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
    />
  </div>
);

interface TextAreaProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  disabled?: boolean;
}

const TextArea: React.FC<TextAreaProps> = ({ label, value, onChange, placeholder, rows = 3, disabled }) => (
  <div className="space-y-1">
    <label className="block text-sm font-medium text-gray-700">{label}</label>
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      disabled={disabled}
      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:bg-gray-100 disabled:cursor-not-allowed"
    />
  </div>
);

interface NumberInputProps {
  label: string;
  value: number | undefined;
  onChange: (value: number | undefined) => void;
  min?: number;
  max?: number;
  placeholder?: string;
  disabled?: boolean;
}

const NumberInput: React.FC<NumberInputProps> = ({ label, value, onChange, min, max, placeholder, disabled }) => (
  <div className="space-y-1">
    <label className="block text-sm font-medium text-gray-700">{label}</label>
    <input
      type="number"
      value={value ?? ''}
      onChange={(e) => {
        const val = e.target.value === '' ? undefined : parseInt(e.target.value, 10);
        onChange(val);
      }}
      min={min}
      max={max}
      placeholder={placeholder}
      disabled={disabled}
      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
    />
  </div>
);

interface SelectInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  disabled?: boolean;
}

const SelectInput: React.FC<SelectInputProps> = ({ label, value, onChange, options, disabled }) => (
  <div className="space-y-1">
    <label className="block text-sm font-medium text-gray-700">{label}</label>
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  </div>
);

interface CheckboxInputProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

const CheckboxInput: React.FC<CheckboxInputProps> = ({ label, checked, onChange, disabled }) => (
  <label className="flex items-center gap-2 cursor-pointer">
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      disabled={disabled}
      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 disabled:cursor-not-allowed"
    />
    <span className="text-sm text-gray-700">{label}</span>
  </label>
);

// ============================================================================
// Node-Specific Property Forms
// ============================================================================

interface TaskPropertiesProps {
  data: TaskNodeData;
  onChange: (updates: Partial<TaskNodeData>) => void;
}

const TaskProperties: React.FC<TaskPropertiesProps> = ({ data, onChange }) => (
  <div className="space-y-4">
    <TextInput
      label="Label"
      value={data.label}
      onChange={(value) => onChange({ label: value })}
    />
    <TextArea
      label="Description"
      value={data.description || ''}
      onChange={(value) => onChange({ description: value })}
      placeholder="Optional description"
    />
    <SelectInput
      label="AI Tool"
      value={data.tool}
      onChange={(value) => onChange({ tool: value as ToolId })}
      options={AVAILABLE_TOOLS.map((t) => ({ value: t.id, label: t.name }))}
    />
    <TextArea
      label="Prompt / Instructions"
      value={data.prompt}
      onChange={(value) => onChange({ prompt: value })}
      placeholder="Enter the task prompt or instructions..."
      rows={5}
    />
    <NumberInput
      label="Timeout (seconds)"
      value={data.timeout}
      onChange={(value) => onChange({ timeout: value })}
      min={0}
      placeholder="No timeout"
    />
    <div className="grid grid-cols-2 gap-3">
      <NumberInput
        label="Retry Count"
        value={data.retryCount}
        onChange={(value) => onChange({ retryCount: value })}
        min={0}
        max={10}
        placeholder="0"
      />
      <NumberInput
        label="Retry Delay (s)"
        value={data.retryDelay}
        onChange={(value) => onChange({ retryDelay: value })}
        min={0}
        placeholder="5"
      />
    </div>
    <TextInput
      label="Output Variable"
      value={data.outputVariable || ''}
      onChange={(value) => onChange({ outputVariable: value || undefined })}
      placeholder="e.g., result"
    />
  </div>
);

interface ConditionPropertiesProps {
  data: ConditionNodeData;
  onChange: (updates: Partial<ConditionNodeData>) => void;
}

const ConditionProperties: React.FC<ConditionPropertiesProps> = ({ data, onChange }) => (
  <div className="space-y-4">
    <TextInput
      label="Label"
      value={data.label}
      onChange={(value) => onChange({ label: value })}
    />
    <TextArea
      label="Description"
      value={data.description || ''}
      onChange={(value) => onChange({ description: value })}
      placeholder="Optional description"
    />
    <SelectInput
      label="Condition Type"
      value={data.conditionType}
      onChange={(value) => onChange({ conditionType: value as ConditionNodeData['conditionType'] })}
      options={[
        { value: 'expression', label: 'Expression' },
        { value: 'status', label: 'Node Status Check' },
        { value: 'output', label: 'Output Check' },
      ]}
    />
    {data.conditionType === 'expression' && (
      <TextArea
        label="Expression"
        value={data.expression || ''}
        onChange={(value) => onChange({ expression: value })}
        placeholder="e.g., ${result.success} === true"
        rows={3}
      />
    )}
    {data.conditionType === 'status' && (
      <>
        <TextInput
          label="Source Node ID"
          value={data.sourceNodeId || ''}
          onChange={(value) => onChange({ sourceNodeId: value })}
          placeholder="Node ID to check"
        />
        <SelectInput
          label="Expected Status"
          value={data.expectedStatus || 'completed'}
          onChange={(value) => onChange({ expectedStatus: value as ConditionNodeData['expectedStatus'] })}
          options={[
            { value: 'completed', label: 'Completed' },
            { value: 'failed', label: 'Failed' },
            { value: 'running', label: 'Running' },
          ]}
        />
      </>
    )}
    {data.conditionType === 'output' && (
      <>
        <SelectInput
          label="Operator"
          value={data.operator || 'equals'}
          onChange={(value) => onChange({ operator: value as ConditionNodeData['operator'] })}
          options={[
            { value: 'equals', label: 'Equals' },
            { value: 'contains', label: 'Contains' },
            { value: 'regex', label: 'Matches Regex' },
            { value: 'greater', label: 'Greater Than' },
            { value: 'less', label: 'Less Than' },
          ]}
        />
        <TextInput
          label="Expected Output"
          value={data.expectedOutput || ''}
          onChange={(value) => onChange({ expectedOutput: value })}
          placeholder="Value to compare"
        />
      </>
    )}
  </div>
);

interface ParallelPropertiesProps {
  data: ParallelNodeData;
  onChange: (updates: Partial<ParallelNodeData>) => void;
}

const ParallelProperties: React.FC<ParallelPropertiesProps> = ({ data, onChange }) => (
  <div className="space-y-4">
    <TextInput
      label="Label"
      value={data.label}
      onChange={(value) => onChange({ label: value })}
    />
    <TextArea
      label="Description"
      value={data.description || ''}
      onChange={(value) => onChange({ description: value })}
      placeholder="Optional description"
    />
    <NumberInput
      label="Max Concurrency"
      value={data.maxConcurrency}
      onChange={(value) => onChange({ maxConcurrency: value })}
      min={1}
      placeholder="Unlimited"
    />
    <CheckboxInput
      label="Wait for all branches to complete"
      checked={data.waitForAll}
      onChange={(checked) => onChange({ waitForAll: checked })}
    />
  </div>
);

interface JoinPropertiesProps {
  data: JoinNodeData;
  onChange: (updates: Partial<JoinNodeData>) => void;
}

const JoinProperties: React.FC<JoinPropertiesProps> = ({ data, onChange }) => (
  <div className="space-y-4">
    <TextInput
      label="Label"
      value={data.label}
      onChange={(value) => onChange({ label: value })}
    />
    <TextArea
      label="Description"
      value={data.description || ''}
      onChange={(value) => onChange({ description: value })}
      placeholder="Optional description"
    />
    <SelectInput
      label="Join Type"
      value={data.joinType}
      onChange={(value) => onChange({ joinType: value as JoinNodeData['joinType'] })}
      options={[
        { value: 'all', label: 'Wait for All' },
        { value: 'any', label: 'First to Complete' },
        { value: 'n_of_m', label: 'N of M Required' },
      ]}
    />
    {data.joinType === 'n_of_m' && (
      <NumberInput
        label="Minimum Required"
        value={data.minRequired}
        onChange={(value) => onChange({ minRequired: value })}
        min={1}
        placeholder="1"
      />
    )}
    <NumberInput
      label="Timeout (seconds)"
      value={data.timeout}
      onChange={(value) => onChange({ timeout: value })}
      min={0}
      placeholder="No timeout"
    />
  </div>
);

interface HumanReviewPropertiesProps {
  data: HumanReviewNodeData;
  onChange: (updates: Partial<HumanReviewNodeData>) => void;
}

const HumanReviewProperties: React.FC<HumanReviewPropertiesProps> = ({ data, onChange }) => {
  const [choicesText, setChoicesText] = useState(data.choices?.join('\n') || '');

  useEffect(() => {
    setChoicesText(data.choices?.join('\n') || '');
  }, [data.choices]);

  const handleChoicesChange = (text: string) => {
    setChoicesText(text);
    const choices = text.split('\n').filter((c) => c.trim() !== '');
    onChange({ choices: choices.length > 0 ? choices : undefined });
  };

  return (
    <div className="space-y-4">
      <TextInput
        label="Label"
        value={data.label}
        onChange={(value) => onChange({ label: value })}
      />
      <TextArea
        label="Description"
        value={data.description || ''}
        onChange={(value) => onChange({ description: value })}
        placeholder="Optional description"
      />
      <SelectInput
        label="Review Type"
        value={data.reviewType}
        onChange={(value) => onChange({ reviewType: value as HumanReviewNodeData['reviewType'] })}
        options={[
          { value: 'approval', label: 'Approval (Yes/No)' },
          { value: 'input', label: 'Text Input Required' },
          { value: 'choice', label: 'Multiple Choice' },
        ]}
      />
      <TextArea
        label="Instructions"
        value={data.instructions}
        onChange={(value) => onChange({ instructions: value })}
        placeholder="Instructions for the reviewer..."
        rows={4}
      />
      {data.reviewType === 'choice' && (
        <TextArea
          label="Choices (one per line)"
          value={choicesText}
          onChange={handleChoicesChange}
          placeholder="Option 1&#10;Option 2&#10;Option 3"
          rows={4}
        />
      )}
      <TextInput
        label="Assignee Email"
        value={data.assigneeEmail || ''}
        onChange={(value) => onChange({ assigneeEmail: value || undefined })}
        placeholder="Optional: email@example.com"
      />
      <div className="grid grid-cols-2 gap-3">
        <NumberInput
          label="Timeout (minutes)"
          value={data.timeoutMinutes}
          onChange={(value) => onChange({ timeoutMinutes: value })}
          min={0}
          placeholder="No timeout"
        />
        <SelectInput
          label="Timeout Action"
          value={data.timeoutAction || ''}
          onChange={(value) => onChange({ timeoutAction: (value || undefined) as HumanReviewNodeData['timeoutAction'] })}
          options={[
            { value: '', label: 'None' },
            { value: 'approve', label: 'Auto Approve' },
            { value: 'reject', label: 'Auto Reject' },
            { value: 'skip', label: 'Skip' },
          ]}
        />
      </div>
    </div>
  );
};

interface LoopPropertiesProps {
  data: LoopNodeData;
  onChange: (updates: Partial<LoopNodeData>) => void;
}

const LoopProperties: React.FC<LoopPropertiesProps> = ({ data, onChange }) => (
  <div className="space-y-4">
    <TextInput
      label="Label"
      value={data.label}
      onChange={(value) => onChange({ label: value })}
    />
    <TextArea
      label="Description"
      value={data.description || ''}
      onChange={(value) => onChange({ description: value })}
      placeholder="Optional description"
    />
    <SelectInput
      label="Loop Type"
      value={data.loopType}
      onChange={(value) => onChange({ loopType: value as LoopNodeData['loopType'] })}
      options={[
        { value: 'count', label: 'Fixed Count' },
        { value: 'while', label: 'While Condition' },
        { value: 'for_each', label: 'For Each Item' },
      ]}
    />
    <NumberInput
      label="Max Iterations"
      value={data.maxIterations}
      onChange={(value) => onChange({ maxIterations: value ?? 10 })}
      min={1}
      max={1000}
    />
    {data.loopType === 'count' && (
      <NumberInput
        label="Count"
        value={data.countValue}
        onChange={(value) => onChange({ countValue: value })}
        min={1}
        placeholder="Number of iterations"
      />
    )}
    {data.loopType === 'while' && (
      <TextArea
        label="While Condition"
        value={data.whileCondition || ''}
        onChange={(value) => onChange({ whileCondition: value })}
        placeholder="e.g., ${retryCount} < 5"
        rows={2}
      />
    )}
    {data.loopType === 'for_each' && (
      <>
        <TextInput
          label="Source Variable"
          value={data.forEachSource || ''}
          onChange={(value) => onChange({ forEachSource: value })}
          placeholder="e.g., ${items}"
        />
        <TextInput
          label="Item Variable"
          value={data.forEachVariable || ''}
          onChange={(value) => onChange({ forEachVariable: value })}
          placeholder="e.g., item"
        />
      </>
    )}
  </div>
);

// ============================================================================
// PropertyPanel Component
// ============================================================================

export const PropertyPanel: React.FC<PropertyPanelProps> = ({ isOpen, onToggle }) => {
  const selectedNode = useSelectedNode();
  const { updateNode, deleteNode, duplicateNode, clearSelection } = useWorkflowStore();

  const handleChange = useCallback(
    (updates: Partial<WorkflowNodeData>) => {
      if (selectedNode) {
        updateNode(selectedNode.id, updates);
      }
    },
    [selectedNode, updateNode]
  );

  const handleDelete = useCallback(() => {
    if (selectedNode) {
      deleteNode(selectedNode.id);
      clearSelection();
    }
  }, [selectedNode, deleteNode, clearSelection]);

  const handleDuplicate = useCallback(() => {
    if (selectedNode) {
      duplicateNode(selectedNode.id);
    }
  }, [selectedNode, duplicateNode]);

  if (!isOpen) {
    return (
      <div className="absolute right-0 top-0 h-full">
        <button
          onClick={onToggle}
          className="m-2 p-2 bg-white rounded-lg shadow-lg hover:bg-gray-50 transition-colors"
          title="Open Property Panel"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="w-80 h-full bg-white border-l border-gray-200 flex flex-col shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h3 className="font-semibold text-gray-800">Properties</h3>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
          title="Close Panel"
        >
          <CloseIcon />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {selectedNode ? (
          <div className="p-4">
            {/* Node Type Badge */}
            <div className="mb-4 flex items-center gap-2">
              <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded-full uppercase">
                {selectedNode.type}
              </span>
              <span className="text-xs text-gray-500">ID: {selectedNode.id.substring(0, 12)}...</span>
            </div>

            {/* Node-Specific Properties */}
            {isTaskNodeData(selectedNode.data) && (
              <TaskProperties data={selectedNode.data} onChange={handleChange} />
            )}
            {isConditionNodeData(selectedNode.data) && (
              <ConditionProperties data={selectedNode.data} onChange={handleChange} />
            )}
            {isParallelNodeData(selectedNode.data) && (
              <ParallelProperties data={selectedNode.data} onChange={handleChange} />
            )}
            {isJoinNodeData(selectedNode.data) && (
              <JoinProperties data={selectedNode.data} onChange={handleChange} />
            )}
            {isHumanReviewNodeData(selectedNode.data) && (
              <HumanReviewProperties data={selectedNode.data} onChange={handleChange} />
            )}
            {isLoopNodeData(selectedNode.data) && (
              <LoopProperties data={selectedNode.data} onChange={handleChange} />
            )}

            {/* Actions */}
            <div className="mt-6 pt-4 border-t border-gray-200 space-y-2">
              <button
                onClick={handleDuplicate}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                <DuplicateIcon />
                Duplicate Node
              </button>
              <button
                onClick={handleDelete}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
              >
                <TrashIcon />
                Delete Node
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 p-4">
            <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
            </svg>
            <p className="text-center">
              Select a node to view and edit its properties
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PropertyPanel;
