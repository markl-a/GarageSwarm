/**
 * WorkerForm Component
 *
 * A form for adding or editing worker configuration.
 * Includes name, description, tools selection, and activation status.
 */

import React, { useState, useEffect } from 'react';
import { WorkerFormData, ToolName, Worker } from '../../types/worker';
import { getAvailableTools, getToolDisplayName } from '../../stores/workerStore';

// ============================================================================
// Types
// ============================================================================

interface WorkerFormProps {
  worker?: Worker;
  onSubmit: (data: WorkerFormData) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

interface ToolCheckboxProps {
  tool: ToolName;
  checked: boolean;
  onChange: (tool: ToolName, checked: boolean) => void;
}

// ============================================================================
// Icons
// ============================================================================

const XMarkIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const CheckIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
  </svg>
);

const LoadingSpinner: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={`animate-spin ${className}`} fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path
      className="opacity-75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    />
  </svg>
);

// ============================================================================
// Tool Icons
// ============================================================================

const ClaudeIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
  </svg>
);

const GeminiIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
  </svg>
);

const OllamaIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h10v2H7z" />
  </svg>
);

const getToolIcon = (tool: ToolName): React.FC<{ className?: string }> => {
  switch (tool) {
    case 'claude_code':
      return ClaudeIcon;
    case 'gemini_cli':
      return GeminiIcon;
    case 'ollama':
      return OllamaIcon;
    default:
      return ClaudeIcon;
  }
};

const getToolColor = (tool: ToolName): string => {
  switch (tool) {
    case 'claude_code':
      return 'border-orange-300 bg-orange-50 text-orange-700';
    case 'gemini_cli':
      return 'border-blue-300 bg-blue-50 text-blue-700';
    case 'ollama':
      return 'border-purple-300 bg-purple-50 text-purple-700';
    default:
      return 'border-gray-300 bg-gray-50 text-gray-700';
  }
};

const getToolCheckedColor = (tool: ToolName): string => {
  switch (tool) {
    case 'claude_code':
      return 'border-orange-500 bg-orange-100 ring-2 ring-orange-200';
    case 'gemini_cli':
      return 'border-blue-500 bg-blue-100 ring-2 ring-blue-200';
    case 'ollama':
      return 'border-purple-500 bg-purple-100 ring-2 ring-purple-200';
    default:
      return 'border-gray-500 bg-gray-100 ring-2 ring-gray-200';
  }
};

// ============================================================================
// Subcomponents
// ============================================================================

const ToolCheckbox: React.FC<ToolCheckboxProps> = ({ tool, checked, onChange }) => {
  const Icon = getToolIcon(tool);
  const baseColor = getToolColor(tool);
  const checkedColor = getToolCheckedColor(tool);

  return (
    <label
      className={`
        relative flex items-center gap-3 p-4 rounded-lg border-2 cursor-pointer
        transition-all hover:shadow-sm
        ${checked ? checkedColor : baseColor}
      `}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(tool, e.target.checked)}
        className="sr-only"
      />
      <div className="flex-shrink-0">
        <Icon className="w-8 h-8" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium">{getToolDisplayName(tool)}</p>
        <p className="text-sm opacity-75">
          {tool === 'claude_code' && 'Anthropic Claude Code CLI'}
          {tool === 'gemini_cli' && 'Google Gemini CLI'}
          {tool === 'ollama' && 'Local Ollama models'}
        </p>
      </div>
      <div
        className={`
          w-5 h-5 rounded-full border-2 flex items-center justify-center
          transition-colors
          ${checked ? 'border-current bg-current' : 'border-gray-300'}
        `}
      >
        {checked && <CheckIcon className="w-3 h-3 text-white" />}
      </div>
    </label>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const WorkerForm: React.FC<WorkerFormProps> = ({
  worker,
  onSubmit,
  onCancel,
  isSubmitting = false,
}) => {
  const isEditing = !!worker;
  const availableTools = getAvailableTools();

  // Form state
  const [formData, setFormData] = useState<WorkerFormData>({
    machine_name: worker?.machine_name ?? '',
    description: '',
    tools: worker?.tools ?? [],
    is_active: worker?.is_active ?? true,
  });

  const [errors, setErrors] = useState<Partial<Record<keyof WorkerFormData, string>>>({});

  // Update form when worker changes
  useEffect(() => {
    if (worker) {
      setFormData({
        machine_name: worker.machine_name,
        description: '',
        tools: worker.tools,
        is_active: worker.is_active ?? true,
      });
    }
  }, [worker]);

  // Validation
  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof WorkerFormData, string>> = {};

    if (!formData.machine_name.trim()) {
      newErrors.machine_name = 'Name is required';
    } else if (formData.machine_name.length < 2) {
      newErrors.machine_name = 'Name must be at least 2 characters';
    } else if (formData.machine_name.length > 100) {
      newErrors.machine_name = 'Name must be less than 100 characters';
    }

    if (formData.tools.length === 0) {
      newErrors.tools = 'At least one tool must be selected';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handlers
  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error when user types
    if (errors[name as keyof WorkerFormData]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleToolChange = (tool: ToolName, checked: boolean) => {
    setFormData((prev) => ({
      ...prev,
      tools: checked
        ? [...prev.tools, tool]
        : prev.tools.filter((t) => t !== tool),
    }));
    // Clear tools error when selection changes
    if (errors.tools) {
      setErrors((prev) => ({ ...prev, tools: undefined }));
    }
  };

  const handleActiveChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, is_active: e.target.checked }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      await onSubmit(formData);
    } catch (error) {
      console.error('Form submission error:', error);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onCancel}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-lg bg-white rounded-xl shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              {isEditing ? 'Edit Worker' : 'Add New Worker'}
            </h2>
            <button
              onClick={onCancel}
              className="p-1 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div className="px-6 py-4 space-y-6">
              {/* Name field */}
              <div>
                <label
                  htmlFor="machine_name"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Worker Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="machine_name"
                  name="machine_name"
                  value={formData.machine_name}
                  onChange={handleInputChange}
                  placeholder="e.g., My Development Machine"
                  className={`
                    w-full px-3 py-2 rounded-lg border shadow-sm
                    focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                    ${errors.machine_name ? 'border-red-300' : 'border-gray-300'}
                  `}
                />
                {errors.machine_name && (
                  <p className="mt-1 text-sm text-red-600">{errors.machine_name}</p>
                )}
              </div>

              {/* Description field */}
              <div>
                <label
                  htmlFor="description"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Description
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  rows={3}
                  placeholder="Optional description for this worker..."
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                />
              </div>

              {/* Tools selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Available Tools <span className="text-red-500">*</span>
                </label>
                <div className="space-y-3">
                  {availableTools.map((tool) => (
                    <ToolCheckbox
                      key={tool}
                      tool={tool}
                      checked={formData.tools.includes(tool)}
                      onChange={handleToolChange}
                    />
                  ))}
                </div>
                {errors.tools && (
                  <p className="mt-2 text-sm text-red-600">{errors.tools}</p>
                )}
              </div>

              {/* Active toggle */}
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">Worker Active</p>
                  <p className="text-sm text-gray-500">
                    Enable this worker to receive and execute tasks
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={handleActiveChange}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-100 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600" />
                </label>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 bg-gray-50 border-t border-gray-200 rounded-b-xl">
              <button
                type="button"
                onClick={onCancel}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <>
                    <LoadingSpinner className="w-4 h-4 mr-2" />
                    {isEditing ? 'Saving...' : 'Creating...'}
                  </>
                ) : (
                  <>{isEditing ? 'Save Changes' : 'Create Worker'}</>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default WorkerForm;
