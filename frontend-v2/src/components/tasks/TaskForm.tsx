/**
 * TaskForm Component
 *
 * Form for creating and editing tasks with validation and JSON editor.
 */

import React, { useState, useEffect, useCallback } from 'react';
import type { Task, TaskCreate, ToolType } from '../../types/task';

interface TaskFormProps {
  task?: Task | null;
  onSubmit: (data: TaskCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
  workers?: Array<{ worker_id: string; name: string; status: string }>;
}

/**
 * Available tool options
 */
const TOOL_OPTIONS: Array<{ value: ToolType | ''; label: string; description: string }> = [
  { value: '', label: 'Auto Select', description: 'Let the system choose the best tool' },
  { value: 'claude_code', label: 'Claude Code', description: 'Anthropic Claude for coding tasks' },
  { value: 'gemini_cli', label: 'Gemini CLI', description: 'Google Gemini for analysis' },
  { value: 'ollama', label: 'Ollama', description: 'Local Ollama models' },
];

/**
 * Priority options
 */
const PRIORITY_OPTIONS = [
  { value: 1, label: 'Lowest', color: 'text-gray-500' },
  { value: 3, label: 'Low', color: 'text-gray-600' },
  { value: 5, label: 'Normal', color: 'text-blue-600' },
  { value: 7, label: 'High', color: 'text-orange-600' },
  { value: 10, label: 'Critical', color: 'text-red-600' },
];

/**
 * JSON Editor component for input parameters
 */
function JsonEditor({
  value,
  onChange,
  error,
}: {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}) {
  const [localValue, setLocalValue] = useState(value);
  const [isValid, setIsValid] = useState(true);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleChange = (newValue: string) => {
    setLocalValue(newValue);

    // Validate JSON
    if (newValue.trim() === '' || newValue.trim() === '{}') {
      setIsValid(true);
      onChange(newValue);
      return;
    }

    try {
      JSON.parse(newValue);
      setIsValid(true);
      onChange(newValue);
    } catch {
      setIsValid(false);
    }
  };

  const formatJson = () => {
    try {
      const parsed = JSON.parse(localValue);
      const formatted = JSON.stringify(parsed, null, 2);
      setLocalValue(formatted);
      onChange(formatted);
      setIsValid(true);
    } catch {
      // Keep current value if invalid
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <label className="block text-sm font-medium text-gray-700">
          Input Parameters (JSON)
        </label>
        <button
          type="button"
          onClick={formatJson}
          className="text-xs text-blue-600 hover:text-blue-800"
          disabled={!isValid}
        >
          Format JSON
        </button>
      </div>
      <textarea
        value={localValue}
        onChange={(e) => handleChange(e.target.value)}
        rows={8}
        className={`
          w-full px-3 py-2 border rounded-md font-mono text-sm
          focus:outline-none focus:ring-2
          ${
            isValid
              ? 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'
              : 'border-red-500 focus:ring-red-500 focus:border-red-500'
          }
        `}
        placeholder='{\n  "key": "value"\n}'
        spellCheck={false}
      />
      {!isValid && (
        <p className="text-sm text-red-600">Invalid JSON format</p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}

/**
 * Form field wrapper component
 */
function FormField({
  label,
  required,
  error,
  children,
  helpText,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
  helpText?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {helpText && <p className="text-xs text-gray-500">{helpText}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}

/**
 * Main TaskForm component
 */
export function TaskForm({
  task,
  onSubmit,
  onCancel,
  isLoading = false,
  workers = [],
}: TaskFormProps) {
  const isEditing = !!task;

  // Form state
  const [description, setDescription] = useState(task?.description || '');
  const [toolPreference, setToolPreference] = useState(task?.tool_preference || '');
  const [workerId, setWorkerId] = useState(task?.worker_id || '');
  const [priority, setPriority] = useState(task?.priority || 5);
  const [inputParameters, setInputParameters] = useState('{}');

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Reset form when task changes
  useEffect(() => {
    if (task) {
      setDescription(task.description);
      setToolPreference(task.tool_preference || '');
      setWorkerId(task.worker_id || '');
      setPriority(task.priority);
      setInputParameters(JSON.stringify(task.result || {}, null, 2));
    } else {
      setDescription('');
      setToolPreference('');
      setWorkerId('');
      setPriority(5);
      setInputParameters('{}');
    }
    setErrors({});
  }, [task]);

  // Validate form
  const validate = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    if (!description.trim()) {
      newErrors.description = 'Description is required';
    } else if (description.length > 10000) {
      newErrors.description = 'Description must be less than 10,000 characters';
    }

    if (inputParameters.trim() && inputParameters.trim() !== '{}') {
      try {
        JSON.parse(inputParameters);
      } catch {
        newErrors.inputParameters = 'Invalid JSON format';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [description, inputParameters]);

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    let metadata: Record<string, unknown> | undefined;
    try {
      const parsed = JSON.parse(inputParameters);
      if (Object.keys(parsed).length > 0) {
        metadata = parsed;
      }
    } catch {
      // Ignore parse errors - already validated
    }

    const data: TaskCreate = {
      description: description.trim(),
      tool_preference: toolPreference || undefined,
      priority,
      metadata,
    };

    onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Description */}
      <FormField
        label="Task Description"
        required
        error={errors.description}
        helpText="Describe what you want the AI to accomplish"
      >
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          className={`
            w-full px-3 py-2 border rounded-md
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            ${errors.description ? 'border-red-500' : 'border-gray-300'}
          `}
          placeholder="Enter a detailed description of the task..."
          disabled={isLoading}
        />
        <div className="text-xs text-gray-400 text-right">
          {description.length}/10,000
        </div>
      </FormField>

      {/* Tool Selection */}
      <FormField
        label="AI Tool"
        helpText="Select the AI tool to use for this task"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {TOOL_OPTIONS.map((option) => (
            <label
              key={option.value}
              className={`
                relative flex items-start p-3 border rounded-lg cursor-pointer
                transition-colors hover:bg-gray-50
                ${
                  toolPreference === option.value
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200'
                }
              `}
            >
              <input
                type="radio"
                name="tool"
                value={option.value}
                checked={toolPreference === option.value}
                onChange={(e) => setToolPreference(e.target.value)}
                className="sr-only"
                disabled={isLoading}
              />
              <div className="flex-1">
                <span className="block text-sm font-medium text-gray-900">
                  {option.label}
                </span>
                <span className="block text-xs text-gray-500">
                  {option.description}
                </span>
              </div>
              {toolPreference === option.value && (
                <svg
                  className="w-5 h-5 text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </label>
          ))}
        </div>
      </FormField>

      {/* Worker Assignment (Optional) */}
      {workers.length > 0 && (
        <FormField
          label="Assign to Worker (Optional)"
          helpText="Leave empty for automatic assignment"
        >
          <select
            value={workerId}
            onChange={(e) => setWorkerId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          >
            <option value="">Auto-assign</option>
            {workers.map((worker) => (
              <option
                key={worker.worker_id}
                value={worker.worker_id}
                disabled={worker.status !== 'online'}
              >
                {worker.name} ({worker.status})
              </option>
            ))}
          </select>
        </FormField>
      )}

      {/* Priority */}
      <FormField label="Priority" helpText="Higher priority tasks are processed first">
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="1"
            max="10"
            value={priority}
            onChange={(e) => setPriority(Number(e.target.value))}
            className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            disabled={isLoading}
          />
          <span
            className={`
              text-sm font-medium w-20 text-center
              ${PRIORITY_OPTIONS.find((p) => p.value <= priority)?.color || 'text-gray-600'}
            `}
          >
            {priority}/10
            <span className="block text-xs">
              {PRIORITY_OPTIONS.find(
                (p, i, arr) =>
                  priority <= p.value ||
                  (i === arr.length - 1 && priority > arr[arr.length - 2].value)
              )?.label || 'Normal'}
            </span>
          </span>
        </div>
      </FormField>

      {/* Input Parameters (JSON) */}
      <JsonEditor
        value={inputParameters}
        onChange={setInputParameters}
        error={errors.inputParameters}
      />

      {/* Form Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading && (
            <svg
              className="w-4 h-4 mr-2 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          )}
          {isEditing ? 'Update Task' : 'Create Task'}
        </button>
      </div>
    </form>
  );
}

export default TaskForm;
