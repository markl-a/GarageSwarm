import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** The visual style variant of the button */
  variant?: ButtonVariant;
  /** The size of the button */
  size?: ButtonSize;
  /** Whether the button should take full width */
  fullWidth?: boolean;
  /** Whether the button is in a loading state */
  isLoading?: boolean;
  /** Icon to display before the button text */
  leftIcon?: ReactNode;
  /** Icon to display after the button text */
  rightIcon?: ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Button content */
  children?: ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: [
    'bg-brand-500 text-white',
    'hover:bg-brand-600',
    'active:bg-brand-700',
    'dark:bg-brand-600 dark:hover:bg-brand-500 dark:active:bg-brand-700',
    'shadow-sm hover:shadow-md',
  ].join(' '),
  secondary: [
    'bg-slate-100 text-slate-900',
    'hover:bg-slate-200',
    'active:bg-slate-300',
    'dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600 dark:active:bg-slate-500',
  ].join(' '),
  outline: [
    'bg-transparent border-2 border-brand-500 text-brand-500',
    'hover:bg-brand-50 hover:border-brand-600 hover:text-brand-600',
    'active:bg-brand-100',
    'dark:border-brand-400 dark:text-brand-400',
    'dark:hover:bg-brand-950 dark:hover:border-brand-300 dark:hover:text-brand-300',
  ].join(' '),
  ghost: [
    'bg-transparent text-slate-700',
    'hover:bg-slate-100',
    'active:bg-slate-200',
    'dark:text-slate-300 dark:hover:bg-slate-800 dark:active:bg-slate-700',
  ].join(' '),
  danger: [
    'bg-red-500 text-white',
    'hover:bg-red-600',
    'active:bg-red-700',
    'dark:bg-red-600 dark:hover:bg-red-500 dark:active:bg-red-700',
    'shadow-sm hover:shadow-md',
  ].join(' '),
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-base gap-2',
  lg: 'px-6 py-3 text-lg gap-2.5',
};

const iconSizeStyles: Record<ButtonSize, string> = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
};

/**
 * Button component with multiple variants and sizes.
 * Supports loading state, icons, and full accessibility.
 *
 * @example
 * ```tsx
 * <Button variant="primary" size="md">
 *   Click me
 * </Button>
 *
 * <Button variant="outline" isLoading>
 *   Submitting...
 * </Button>
 *
 * <Button variant="ghost" leftIcon={<IconPlus />}>
 *   Add Item
 * </Button>
 * ```
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      fullWidth = false,
      isLoading = false,
      leftIcon,
      rightIcon,
      className = '',
      children,
      disabled,
      type = 'button',
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading;

    const baseStyles = [
      'inline-flex items-center justify-center',
      'font-medium rounded-lg',
      'transition-all duration-200',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2',
      'dark:focus-visible:ring-offset-dark-bg',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
    ].join(' ');

    const widthStyle = fullWidth ? 'w-full' : '';

    const combinedClassName = [
      baseStyles,
      variantStyles[variant],
      sizeStyles[size],
      widthStyle,
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={combinedClassName}
        aria-disabled={isDisabled}
        aria-busy={isLoading}
        {...props}
      >
        {isLoading && (
          <svg
            className={`animate-spin ${iconSizeStyles[size]}`}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
            data-testid="loading-spinner"
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
        {!isLoading && leftIcon && (
          <span className={`flex-shrink-0 ${iconSizeStyles[size]}`} aria-hidden="true">
            {leftIcon}
          </span>
        )}
        {children && <span>{children}</span>}
        {!isLoading && rightIcon && (
          <span className={`flex-shrink-0 ${iconSizeStyles[size]}`} aria-hidden="true">
            {rightIcon}
          </span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
