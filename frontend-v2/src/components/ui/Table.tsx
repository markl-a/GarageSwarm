import {
  forwardRef,
  type HTMLAttributes,
  type ThHTMLAttributes,
  type TdHTMLAttributes,
  type ReactNode,
} from 'react';

export interface TableProps extends HTMLAttributes<HTMLTableElement> {
  /** Whether the table should have striped rows */
  striped?: boolean;
  /** Whether the table rows should have hover effect */
  hoverable?: boolean;
  /** Whether the table should be compact */
  compact?: boolean;
  /** Whether to show borders between cells */
  bordered?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Table content */
  children?: ReactNode;
}

export interface TableHeaderProps extends HTMLAttributes<HTMLTableSectionElement> {
  /** Additional CSS classes */
  className?: string;
  /** Header content */
  children?: ReactNode;
}

export interface TableBodyProps extends HTMLAttributes<HTMLTableSectionElement> {
  /** Additional CSS classes */
  className?: string;
  /** Body content */
  children?: ReactNode;
}

export interface TableFooterProps extends HTMLAttributes<HTMLTableSectionElement> {
  /** Additional CSS classes */
  className?: string;
  /** Footer content */
  children?: ReactNode;
}

export interface TableRowProps extends HTMLAttributes<HTMLTableRowElement> {
  /** Whether the row is selected */
  selected?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Row content */
  children?: ReactNode;
}

export interface TableHeadProps extends ThHTMLAttributes<HTMLTableCellElement> {
  /** Whether the column is sortable */
  sortable?: boolean;
  /** Current sort direction */
  sortDirection?: 'asc' | 'desc' | null;
  /** Callback when sort is requested */
  onSort?: () => void;
  /** Additional CSS classes */
  className?: string;
  /** Cell content */
  children?: ReactNode;
}

export interface TableCellProps extends TdHTMLAttributes<HTMLTableCellElement> {
  /** Additional CSS classes */
  className?: string;
  /** Cell content */
  children?: ReactNode;
}

export interface TableCaptionProps extends HTMLAttributes<HTMLTableCaptionElement> {
  /** Position of the caption */
  position?: 'top' | 'bottom';
  /** Additional CSS classes */
  className?: string;
  /** Caption content */
  children?: ReactNode;
}

/**
 * Table component for displaying tabular data.
 *
 * @example
 * ```tsx
 * <Table striped hoverable>
 *   <TableHeader>
 *     <TableRow>
 *       <TableHead sortable sortDirection="asc" onSort={() => {}}>Name</TableHead>
 *       <TableHead>Status</TableHead>
 *       <TableHead>Date</TableHead>
 *     </TableRow>
 *   </TableHeader>
 *   <TableBody>
 *     <TableRow>
 *       <TableCell>John Doe</TableCell>
 *       <TableCell><Badge variant="success">Active</Badge></TableCell>
 *       <TableCell>2024-01-15</TableCell>
 *     </TableRow>
 *   </TableBody>
 * </Table>
 * ```
 */
export const Table = forwardRef<HTMLTableElement, TableProps>(
  (
    {
      striped = false,
      hoverable = false,
      compact = false,
      bordered = false,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = [
      'w-full text-left',
      'border-collapse',
    ].join(' ');

    // Pass context through data attributes
    const dataAttrs = {
      'data-striped': striped,
      'data-hoverable': hoverable,
      'data-compact': compact,
      'data-bordered': bordered,
    };

    return (
      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-dark-border">
        <table
          ref={ref}
          className={`${baseStyles} ${className}`}
          {...dataAttrs}
          {...props}
        >
          {children}
        </table>
      </div>
    );
  }
);

Table.displayName = 'Table';

/**
 * TableHeader component for table header section.
 */
export const TableHeader = forwardRef<HTMLTableSectionElement, TableHeaderProps>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <thead
        ref={ref}
        className={`bg-slate-50 dark:bg-slate-800/50 ${className}`}
        {...props}
      >
        {children}
      </thead>
    );
  }
);

TableHeader.displayName = 'TableHeader';

/**
 * TableBody component for table body section.
 */
export const TableBody = forwardRef<HTMLTableSectionElement, TableBodyProps>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <tbody
        ref={ref}
        className={`divide-y divide-slate-200 dark:divide-dark-border ${className}`}
        {...props}
      >
        {children}
      </tbody>
    );
  }
);

TableBody.displayName = 'TableBody';

/**
 * TableFooter component for table footer section.
 */
export const TableFooter = forwardRef<HTMLTableSectionElement, TableFooterProps>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <tfoot
        ref={ref}
        className={`bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-dark-border ${className}`}
        {...props}
      >
        {children}
      </tfoot>
    );
  }
);

TableFooter.displayName = 'TableFooter';

/**
 * TableRow component for table rows.
 */
export const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ selected = false, className = '', children, ...props }, ref) => {
    const selectedStyles = selected
      ? 'bg-brand-50 dark:bg-brand-900/20'
      : '';

    // Use CSS for striped and hoverable based on parent table's data attributes
    const baseStyles = [
      'transition-colors duration-150',
      '[table[data-striped="true"]_&:nth-child(even)]:bg-slate-50',
      'dark:[table[data-striped="true"]_&:nth-child(even)]:bg-slate-800/30',
      '[table[data-hoverable="true"]_&]:hover:bg-slate-100',
      'dark:[table[data-hoverable="true"]_&]:hover:bg-slate-800/50',
    ].join(' ');

    return (
      <tr
        ref={ref}
        className={`${baseStyles} ${selectedStyles} ${className}`}
        aria-selected={selected}
        {...props}
      >
        {children}
      </tr>
    );
  }
);

TableRow.displayName = 'TableRow';

/**
 * TableHead component for header cells.
 */
export const TableHead = forwardRef<HTMLTableCellElement, TableHeadProps>(
  (
    {
      sortable = false,
      sortDirection = null,
      onSort,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = [
      'px-4 py-3',
      'text-sm font-semibold text-slate-700 dark:text-slate-300',
      'text-left',
      '[table[data-compact="true"]_&]:px-3 [table[data-compact="true"]_&]:py-2',
      '[table[data-bordered="true"]_&]:border-r [table[data-bordered="true"]_&]:border-slate-200',
      'dark:[table[data-bordered="true"]_&]:border-dark-border',
      '[table[data-bordered="true"]_&:last-child]:border-r-0',
    ].join(' ');

    const sortableStyles = sortable
      ? 'cursor-pointer select-none hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors'
      : '';

    const handleClick = () => {
      if (sortable && onSort) {
        onSort();
      }
    };

    const handleKeyDown = (event: React.KeyboardEvent) => {
      if (sortable && onSort && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        onSort();
      }
    };

    return (
      <th
        ref={ref}
        className={`${baseStyles} ${sortableStyles} ${className}`}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        tabIndex={sortable ? 0 : undefined}
        aria-sort={
          sortDirection === 'asc'
            ? 'ascending'
            : sortDirection === 'desc'
            ? 'descending'
            : undefined
        }
        {...props}
      >
        <div className="flex items-center gap-2">
          <span>{children}</span>
          {sortable && (
            <span className="flex-shrink-0" aria-hidden="true">
              {sortDirection === 'asc' ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
                </svg>
              ) : sortDirection === 'desc' ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              ) : (
                <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                </svg>
              )}
            </span>
          )}
        </div>
      </th>
    );
  }
);

TableHead.displayName = 'TableHead';

/**
 * TableCell component for data cells.
 */
export const TableCell = forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ className = '', children, ...props }, ref) => {
    const baseStyles = [
      'px-4 py-3',
      'text-sm text-slate-600 dark:text-slate-400',
      '[table[data-compact="true"]_&]:px-3 [table[data-compact="true"]_&]:py-2',
      '[table[data-bordered="true"]_&]:border-r [table[data-bordered="true"]_&]:border-slate-200',
      'dark:[table[data-bordered="true"]_&]:border-dark-border',
      '[table[data-bordered="true"]_&:last-child]:border-r-0',
    ].join(' ');

    return (
      <td ref={ref} className={`${baseStyles} ${className}`} {...props}>
        {children}
      </td>
    );
  }
);

TableCell.displayName = 'TableCell';

/**
 * TableCaption component for table captions.
 */
export const TableCaption = forwardRef<HTMLTableCaptionElement, TableCaptionProps>(
  ({ position = 'bottom', className = '', children, ...props }, ref) => {
    const positionStyles = position === 'top' ? 'caption-top' : 'caption-bottom';

    return (
      <caption
        ref={ref}
        className={`px-4 py-3 text-sm text-slate-500 dark:text-slate-400 ${positionStyles} ${className}`}
        {...props}
      >
        {children}
      </caption>
    );
  }
);

TableCaption.displayName = 'TableCaption';

export default Table;
