import { forwardRef, type HTMLAttributes } from 'react';

export type SpinnerSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
export type SpinnerVariant = 'default' | 'primary' | 'white';

export interface SpinnerProps extends HTMLAttributes<HTMLDivElement> {
  /** Size of the spinner */
  size?: SpinnerSize;
  /** Color variant of the spinner */
  variant?: SpinnerVariant;
  /** Label for screen readers */
  label?: string;
  /** Whether to center the spinner in its container */
  center?: boolean;
  /** Additional CSS classes */
  className?: string;
}

const sizeStyles: Record<SpinnerSize, string> = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
};

const variantStyles: Record<SpinnerVariant, { track: string; spinner: string }> = {
  default: {
    track: 'text-slate-200 dark:text-slate-700',
    spinner: 'text-slate-600 dark:text-slate-400',
  },
  primary: {
    track: 'text-brand-200 dark:text-brand-900',
    spinner: 'text-brand-500 dark:text-brand-400',
  },
  white: {
    track: 'text-white/30',
    spinner: 'text-white',
  },
};

/**
 * Spinner component for loading states.
 *
 * @example
 * ```tsx
 * <Spinner />
 *
 * <Spinner size="lg" variant="primary" />
 *
 * <Spinner size="sm" label="Loading data..." />
 *
 * <Spinner center />
 * ```
 */
export const Spinner = forwardRef<HTMLDivElement, SpinnerProps>(
  (
    {
      size = 'md',
      variant = 'default',
      label = 'Loading...',
      center = false,
      className = '',
      ...props
    },
    ref
  ) => {
    const colors = variantStyles[variant];

    const wrapperClassName = center
      ? `flex items-center justify-center ${className}`
      : className;

    return (
      <div
        ref={ref}
        role="status"
        aria-live="polite"
        className={wrapperClassName}
        {...props}
      >
        <svg
          className={`animate-spin ${sizeStyles[size]}`}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className={`opacity-25 ${colors.track}`}
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className={colors.spinner}
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <span className="sr-only">{label}</span>
      </div>
    );
  }
);

Spinner.displayName = 'Spinner';

/**
 * FullPageSpinner component for loading entire pages.
 */
export interface FullPageSpinnerProps extends SpinnerProps {
  /** Text to display below the spinner */
  text?: string;
}

export const FullPageSpinner = forwardRef<HTMLDivElement, FullPageSpinnerProps>(
  ({ text, size = 'xl', variant = 'primary', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className="fixed inset-0 flex flex-col items-center justify-center bg-white/80 dark:bg-dark-bg/80 backdrop-blur-sm z-50"
        {...props}
      >
        <Spinner size={size} variant={variant} />
        {text && (
          <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">{text}</p>
        )}
      </div>
    );
  }
);

FullPageSpinner.displayName = 'FullPageSpinner';

export default Spinner;
