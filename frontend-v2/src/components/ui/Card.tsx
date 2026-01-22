import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Whether to add padding inside the card */
  padding?: 'none' | 'sm' | 'md' | 'lg';
  /** Whether the card has a hover effect */
  hoverable?: boolean;
  /** Whether to show a border */
  bordered?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Card content */
  children?: ReactNode;
}

export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  /** Title of the card */
  title?: ReactNode;
  /** Subtitle or description */
  subtitle?: ReactNode;
  /** Action elements (buttons, icons, etc.) */
  action?: ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Header content */
  children?: ReactNode;
}

export interface CardContentProps extends HTMLAttributes<HTMLDivElement> {
  /** Additional CSS classes */
  className?: string;
  /** Content */
  children?: ReactNode;
}

export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  /** Alignment of footer content */
  align?: 'left' | 'center' | 'right' | 'between';
  /** Additional CSS classes */
  className?: string;
  /** Footer content */
  children?: ReactNode;
}

const paddingStyles = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

const alignmentStyles = {
  left: 'justify-start',
  center: 'justify-center',
  right: 'justify-end',
  between: 'justify-between',
};

/**
 * Card component for grouping related content.
 *
 * @example
 * ```tsx
 * <Card>
 *   <CardHeader title="Card Title" subtitle="Optional subtitle" />
 *   <CardContent>
 *     Main content goes here
 *   </CardContent>
 *   <CardFooter>
 *     <Button>Action</Button>
 *   </CardFooter>
 * </Card>
 * ```
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      padding = 'none',
      hoverable = false,
      bordered = true,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = [
      'bg-white dark:bg-dark-card',
      'rounded-xl',
      'shadow-sm',
      'overflow-hidden',
    ].join(' ');

    const borderStyles = bordered
      ? 'border border-slate-200 dark:border-dark-border'
      : '';

    const hoverStyles = hoverable
      ? 'transition-all duration-200 hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 cursor-pointer'
      : '';

    const combinedClassName = [
      baseStyles,
      borderStyles,
      hoverStyles,
      paddingStyles[padding],
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div ref={ref} className={combinedClassName} {...props}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

/**
 * CardHeader component for displaying title and actions.
 */
export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ title, subtitle, action, className = '', children, ...props }, ref) => {
    const baseStyles = [
      'px-4 py-4 sm:px-6',
      'border-b border-slate-200 dark:border-dark-border',
    ].join(' ');

    const combinedClassName = [baseStyles, className].filter(Boolean).join(' ');

    return (
      <div ref={ref} className={combinedClassName} {...props}>
        {children || (
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              {title && (
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400 truncate">
                  {subtitle}
                </p>
              )}
            </div>
            {action && <div className="flex-shrink-0">{action}</div>}
          </div>
        )}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

/**
 * CardContent component for main content area.
 */
export const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({ className = '', children, ...props }, ref) => {
    const baseStyles = 'px-4 py-4 sm:px-6';

    const combinedClassName = [baseStyles, className].filter(Boolean).join(' ');

    return (
      <div ref={ref} className={combinedClassName} {...props}>
        {children}
      </div>
    );
  }
);

CardContent.displayName = 'CardContent';

/**
 * CardFooter component for actions and additional info.
 */
export const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({ align = 'right', className = '', children, ...props }, ref) => {
    const baseStyles = [
      'px-4 py-3 sm:px-6',
      'bg-slate-50 dark:bg-slate-800/50',
      'border-t border-slate-200 dark:border-dark-border',
      'flex items-center gap-3',
    ].join(' ');

    const combinedClassName = [baseStyles, alignmentStyles[align], className]
      .filter(Boolean)
      .join(' ');

    return (
      <div ref={ref} className={combinedClassName} {...props}>
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';

export default Card;
