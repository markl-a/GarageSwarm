/**
 * NodePalette - Draggable node palette component
 *
 * Displays available node types grouped by category with drag-and-drop
 * functionality to add nodes to the canvas.
 */

import React, { useState, useMemo, useCallback } from 'react';
import type { WorkflowNodeType } from '@/types/workflow';
import { NODE_PALETTE_ITEMS } from '@/types/workflow';

// ============================================================================
// Icons
// ============================================================================

const SearchIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const PlayIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const GitBranchIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
  </svg>
);

const GitForkIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

const GitMergeIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
);

const UserCheckIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 8l-3 3-1.5-1.5" />
  </svg>
);

const RepeatIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const ChevronDownIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

// ============================================================================
// Icon Mapping
// ============================================================================

const getNodeIcon = (type: WorkflowNodeType) => {
  switch (type) {
    case 'task':
      return <PlayIcon />;
    case 'condition':
      return <GitBranchIcon />;
    case 'parallel':
      return <GitForkIcon />;
    case 'join':
      return <GitMergeIcon />;
    case 'human_review':
      return <UserCheckIcon />;
    case 'loop':
      return <RepeatIcon />;
    default:
      return <PlayIcon />;
  }
};

const getNodeColor = (type: WorkflowNodeType) => {
  switch (type) {
    case 'task':
      return { bg: 'bg-blue-100', text: 'text-blue-600', border: 'border-blue-300' };
    case 'condition':
      return { bg: 'bg-amber-100', text: 'text-amber-600', border: 'border-amber-300' };
    case 'parallel':
      return { bg: 'bg-teal-100', text: 'text-teal-600', border: 'border-teal-300' };
    case 'join':
      return { bg: 'bg-indigo-100', text: 'text-indigo-600', border: 'border-indigo-300' };
    case 'human_review':
      return { bg: 'bg-purple-100', text: 'text-purple-600', border: 'border-purple-300' };
    case 'loop':
      return { bg: 'bg-orange-100', text: 'text-orange-600', border: 'border-orange-300' };
    default:
      return { bg: 'bg-gray-100', text: 'text-gray-600', border: 'border-gray-300' };
  }
};

// ============================================================================
// Types
// ============================================================================

interface NodePaletteProps {
  isOpen: boolean;
  onToggle: () => void;
}

interface CategoryGroup {
  name: string;
  items: typeof NODE_PALETTE_ITEMS;
}

// ============================================================================
// Draggable Node Item
// ============================================================================

interface DraggableNodeItemProps {
  type: WorkflowNodeType;
  label: string;
  description: string;
}

const DraggableNodeItem: React.FC<DraggableNodeItemProps> = ({ type, label, description }) => {
  const colors = getNodeColor(type);

  const onDragStart = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.dataTransfer.setData('application/reactflow', type);
    event.dataTransfer.effectAllowed = 'move';
  }, [type]);

  return (
    <div
      draggable
      onDragStart={onDragStart}
      className={`
        flex items-center gap-3 p-3 rounded-lg border-2
        ${colors.bg} ${colors.border}
        cursor-grab active:cursor-grabbing
        hover:shadow-md hover:scale-[1.02]
        transition-all duration-200
        select-none
      `}
    >
      <div className={`p-2 rounded-lg bg-white ${colors.text}`}>
        {getNodeIcon(type)}
      </div>
      <div className="flex-1 min-w-0">
        <div className={`font-medium text-sm ${colors.text}`}>{label}</div>
        <div className="text-xs text-gray-500 truncate">{description}</div>
      </div>
      <div className="text-gray-400">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
        </svg>
      </div>
    </div>
  );
};

// ============================================================================
// Category Section
// ============================================================================

interface CategorySectionProps {
  category: CategoryGroup;
  isExpanded: boolean;
  onToggle: () => void;
}

const CategorySection: React.FC<CategorySectionProps> = ({ category, isExpanded, onToggle }) => {
  return (
    <div className="mb-2">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
      >
        {isExpanded ? <ChevronDownIcon /> : <ChevronRightIcon />}
        <span>{category.name}</span>
        <span className="ml-auto text-xs text-gray-400 bg-gray-200 px-1.5 py-0.5 rounded">
          {category.items.length}
        </span>
      </button>
      {isExpanded && (
        <div className="mt-2 space-y-2 pl-2">
          {category.items.map((item) => (
            <DraggableNodeItem
              key={item.type}
              type={item.type}
              label={item.label}
              description={item.description}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// NodePalette Component
// ============================================================================

export const NodePalette: React.FC<NodePaletteProps> = ({ isOpen, onToggle }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['Execution', 'Control Flow', 'Human'])
  );

  // Group items by category
  const categories = useMemo(() => {
    const grouped: Record<string, typeof NODE_PALETTE_ITEMS> = {};

    NODE_PALETTE_ITEMS.forEach((item) => {
      if (!grouped[item.category]) {
        grouped[item.category] = [];
      }
      grouped[item.category].push(item);
    });

    return Object.entries(grouped).map(([name, items]) => ({ name, items }));
  }, []);

  // Filter items by search query
  const filteredCategories = useMemo(() => {
    if (!searchQuery.trim()) {
      return categories;
    }

    const query = searchQuery.toLowerCase();
    return categories
      .map((category) => ({
        ...category,
        items: category.items.filter(
          (item) =>
            item.label.toLowerCase().includes(query) ||
            item.description.toLowerCase().includes(query)
        ),
      }))
      .filter((category) => category.items.length > 0);
  }, [categories, searchQuery]);

  const toggleCategory = useCallback((categoryName: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryName)) {
        next.delete(categoryName);
      } else {
        next.add(categoryName);
      }
      return next;
    });
  }, []);

  if (!isOpen) {
    return (
      <div className="absolute left-0 top-0 h-full">
        <button
          onClick={onToggle}
          className="m-2 p-2 bg-white rounded-lg shadow-lg hover:bg-gray-50 transition-colors"
          title="Open Node Palette"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="w-72 h-full bg-white border-r border-gray-200 flex flex-col shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h3 className="font-semibold text-gray-800">Node Palette</h3>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
          title="Close Palette"
        >
          <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Search */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
            <SearchIcon />
          </span>
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Node List */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {/* Drag Instructions */}
        <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-xs text-blue-700">
            Drag and drop nodes onto the canvas to build your workflow.
          </p>
        </div>

        {/* Categories */}
        {filteredCategories.map((category) => (
          <CategorySection
            key={category.name}
            category={category}
            isExpanded={expandedCategories.has(category.name) || searchQuery.trim() !== ''}
            onToggle={() => toggleCategory(category.name)}
          />
        ))}

        {/* No Results */}
        {filteredCategories.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <svg className="w-12 h-12 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm">No nodes found</p>
            <p className="text-xs mt-1">Try a different search term</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
        <p className="text-xs text-gray-500 text-center">
          {NODE_PALETTE_ITEMS.length} node types available
        </p>
      </div>
    </div>
  );
};

export default NodePalette;
