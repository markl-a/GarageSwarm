/**
 * TaskOutput Component
 *
 * Displays task execution result with JSON syntax highlighting and copy functionality.
 */

import React, { useState, useCallback, useMemo } from 'react';
import type { Task } from '../../types/task';

interface TaskOutputProps {
  task: Task;
  className?: string;
}

/**
 * Copy button component with feedback
 */
function CopyButton({
  text,
  className = '',
}: {
  text: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md
        transition-colors
        ${
          copied
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        }
        ${className}
      `}
    >
      {copied ? (
        <>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Copied!
        </>
      ) : (
        <>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
          Copy
        </>
      )}
    </button>
  );
}

/**
 * JSON syntax highlighter component
 */
function JsonHighlighter({ json, expanded = true }: { json: string; expanded?: boolean }) {
  // Simple token types for JSON highlighting
  const highlightJson = (text: string): React.ReactNode[] => {
    const tokens: React.ReactNode[] = [];
    let i = 0;
    let key = 0;

    const addToken = (content: string, className: string) => {
      tokens.push(
        <span key={key++} className={className}>
          {content}
        </span>
      );
    };

    while (i < text.length) {
      const char = text[i];

      // Whitespace
      if (/\s/.test(char)) {
        let whitespace = '';
        while (i < text.length && /\s/.test(text[i])) {
          whitespace += text[i];
          i++;
        }
        addToken(whitespace, '');
        continue;
      }

      // String
      if (char === '"') {
        let str = '"';
        i++;
        while (i < text.length && text[i] !== '"') {
          if (text[i] === '\\' && i + 1 < text.length) {
            str += text[i] + text[i + 1];
            i += 2;
          } else {
            str += text[i];
            i++;
          }
        }
        str += '"';
        i++;

        // Check if this is a key (followed by colon)
        let nextNonWhitespace = i;
        while (nextNonWhitespace < text.length && /\s/.test(text[nextNonWhitespace])) {
          nextNonWhitespace++;
        }

        if (text[nextNonWhitespace] === ':') {
          addToken(str, 'text-purple-600'); // Key
        } else {
          addToken(str, 'text-green-600'); // String value
        }
        continue;
      }

      // Number
      if (/[-\d]/.test(char)) {
        let num = '';
        while (i < text.length && /[-\d.eE+]/.test(text[i])) {
          num += text[i];
          i++;
        }
        addToken(num, 'text-blue-600');
        continue;
      }

      // Boolean and null
      if (text.slice(i, i + 4) === 'true') {
        addToken('true', 'text-orange-600');
        i += 4;
        continue;
      }
      if (text.slice(i, i + 5) === 'false') {
        addToken('false', 'text-orange-600');
        i += 5;
        continue;
      }
      if (text.slice(i, i + 4) === 'null') {
        addToken('null', 'text-gray-500');
        i += 4;
        continue;
      }

      // Punctuation
      if (/[{}\[\]:,]/.test(char)) {
        addToken(char, 'text-gray-700');
        i++;
        continue;
      }

      // Unknown character
      addToken(char, '');
      i++;
    }

    return tokens;
  };

  return (
    <pre
      className={`
        font-mono text-sm leading-relaxed overflow-x-auto
        ${expanded ? 'whitespace-pre-wrap' : 'whitespace-pre'}
      `}
    >
      {highlightJson(json)}
    </pre>
  );
}

/**
 * Error display component
 */
function ErrorDisplay({ error }: { error: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <svg
          className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <div className="flex-1">
          <h4 className="text-sm font-medium text-red-800">Error</h4>
          <p className="mt-1 text-sm text-red-700 whitespace-pre-wrap">{error}</p>
        </div>
      </div>
    </div>
  );
}

/**
 * Empty state component
 */
function EmptyOutput() {
  return (
    <div className="text-center py-8">
      <svg
        className="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <h3 className="mt-2 text-sm font-medium text-gray-900">No output yet</h3>
      <p className="mt-1 text-sm text-gray-500">
        Task output will appear here once the task completes.
      </p>
    </div>
  );
}

/**
 * Main TaskOutput component
 */
export function TaskOutput({ task, className = '' }: TaskOutputProps) {
  const [viewMode, setViewMode] = useState<'formatted' | 'raw'>('formatted');

  // Format result as JSON string
  const resultJson = useMemo(() => {
    if (!task.result) return null;
    try {
      return JSON.stringify(task.result, null, 2);
    } catch {
      return String(task.result);
    }
  }, [task.result]);

  // Raw result string for copying
  const rawResult = useMemo(() => {
    if (!task.result) return '';
    try {
      return JSON.stringify(task.result, null, 2);
    } catch {
      return String(task.result);
    }
  }, [task.result]);

  // Show error if task failed
  if (task.error) {
    return (
      <div className={className}>
        <ErrorDisplay error={task.error} />
        {task.result && (
          <div className="mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Partial Result
            </h4>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 overflow-auto max-h-96">
              <JsonHighlighter json={resultJson || ''} />
            </div>
          </div>
        )}
      </div>
    );
  }

  // Show empty state if no result
  if (!task.result) {
    return (
      <div className={className}>
        <EmptyOutput />
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header with controls */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-700">Output</h3>
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex rounded-md shadow-sm">
            <button
              onClick={() => setViewMode('formatted')}
              className={`
                px-3 py-1.5 text-xs font-medium rounded-l-md border
                ${
                  viewMode === 'formatted'
                    ? 'bg-blue-50 border-blue-500 text-blue-700'
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                }
              `}
            >
              Formatted
            </button>
            <button
              onClick={() => setViewMode('raw')}
              className={`
                px-3 py-1.5 text-xs font-medium rounded-r-md border-t border-b border-r
                ${
                  viewMode === 'raw'
                    ? 'bg-blue-50 border-blue-500 text-blue-700'
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                }
              `}
            >
              Raw
            </button>
          </div>

          {/* Copy button */}
          <CopyButton text={rawResult} />
        </div>
      </div>

      {/* Output content */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg overflow-hidden">
        <div className="p-4 overflow-auto max-h-[500px]">
          {viewMode === 'formatted' ? (
            <JsonHighlighter json={resultJson || ''} />
          ) : (
            <pre className="font-mono text-sm text-gray-800 whitespace-pre-wrap">
              {rawResult}
            </pre>
          )}
        </div>
      </div>

      {/* Result metadata */}
      <div className="mt-2 text-xs text-gray-500">
        {rawResult.length.toLocaleString()} characters
        {task.completed_at && (
          <span className="ml-2">
            Completed: {new Date(task.completed_at).toLocaleString()}
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Compact output preview for lists
 */
export function TaskOutputPreview({
  result,
  maxLength = 100,
  className = '',
}: {
  result: Record<string, unknown> | null;
  maxLength?: number;
  className?: string;
}) {
  if (!result) {
    return <span className="text-gray-400">No output</span>;
  }

  const preview = useMemo(() => {
    try {
      const json = JSON.stringify(result);
      if (json.length <= maxLength) {
        return json;
      }
      return json.slice(0, maxLength) + '...';
    } catch {
      return String(result).slice(0, maxLength);
    }
  }, [result, maxLength]);

  return (
    <span className={`font-mono text-xs text-gray-600 ${className}`} title={JSON.stringify(result, null, 2)}>
      {preview}
    </span>
  );
}

export default TaskOutput;
