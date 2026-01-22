import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';

export type BadgeVariant = 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info';
export type BadgeSize = 'sm' | 'md' | 'lg';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  /** The visual style variant of the badge */
  variant?: BadgeVariant;
  /** The size of the badge */
  size?: BadgeSize;
  /** Whether the badge has a dot indicator */
  dot?: boolean;
  /** Whether the badge has a pulse animation (for status indicators) */
  pulse?: boolean;
  /** Icon to display before the text */
  icon?: ReactNode;
  /** Whether the badge is removable */
  removable?: boolean;
  /** Callback when remove button is clicked */
  onRemove?: () => void;
  /** Additional CSS classes */
  className?: string;
  /** Badge content */
  children?: ReactNode;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
  primary: 'bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300',
  secondary: 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300',
  success: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300',
  danger: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
};

const dotStyles: Record<BadgeVariant, string> = {
  default: 'bg-slate-500',
  primary: 'bg-brand-500',
  secondary: 'bg-purple-500',
  success: 'bg-green-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
  info: 'bg-blue-500',
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-sm',
  lg: 'px-3 py-1 text-base',
};

const dotSizeStyles: Record<BadgeSize, string> = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-2.5 h-2.5',
};

/**
 * Badge component for status indicators and labels.
 *
 * @example
 * ```tsx
 * <Badge variant="success">Active</Badge>
 *
 * <Badge variant="warning" dot>Pending</Badge>
 *
 * <Badge variant="danger" pulse>Error</Badge>
 *
 * <Badge variant="info" removable onRemove={() => {}}>
 *   Tag
 * </Badge>
 * ```
 */
export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      variant = 'default',
      size = 'md',
      dot = false,
      pulse = false,
      icon,
      removable = false,
      onRemove,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = [
      'inline-flex items-center gap-1.5',
      'font-medium rounded-full',
      'transition-colors duration-200',
    ].join(' ');

    const combinedClassName = [
      baseStyles,
      variantStyles[variant],
      sizeStyles[size],
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <span ref={ref} className={combinedClassName} {...props}>
        {dot && (
          <span className="relative flex-shrink-0">
            <span
              className={`block rounded-full ${dotStyles[variant]} ${dotSizeStyles[size]}`}
              aria-hidden="true"
            />
            {pulse && (
              <span
                className={`absolute inset-0 rounded-full ${dotStyles[variant]} animate-ping opacity-75`}
                aria-hidden="true"
              />
            )}
          </span>
        )}
        {icon && (
          <span className="flex-shrink-0" aria-hidden="true">
            {icon}
          </span>
        )}
        {children}
        {removable && (
          <button
            type="button"
            onClick={onRemove}
            className="flex-shrink-0 ml-0.5 -mr-1 p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-current"
            aria-label="Remove"
          >
            <svg
              className="w-3 h-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export default Badge;
