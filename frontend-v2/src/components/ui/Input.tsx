import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';

export type InputSize = 'sm' | 'md' | 'lg';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Label text for the input */
  label?: string;
  /** Error message to display */
  error?: string;
  /** Helper text to display below the input */
  helperText?: string;
  /** Size of the input */
  size?: InputSize;
  /** Icon to display at the start of the input */
  leftIcon?: ReactNode;
  /** Icon to display at the end of the input */
  rightIcon?: ReactNode;
  /** Whether the input is required */
  required?: boolean;
  /** Additional CSS classes for the wrapper */
  wrapperClassName?: string;
  /** Additional CSS classes */
  className?: string;
}

const sizeStyles: Record<InputSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-3 py-2 text-base',
  lg: 'px-4 py-3 text-lg',
};

const iconSizeStyles: Record<InputSize, string> = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
};

const leftPaddingStyles: Record<InputSize, string> = {
  sm: 'pl-9',
  md: 'pl-10',
  lg: 'pl-12',
};

const rightPaddingStyles: Record<InputSize, string> = {
  sm: 'pr-9',
  md: 'pr-10',
  lg: 'pr-12',
};

/**
 * Input component with label, error state, and icon support.
 *
 * @example
 * ```tsx
 * <Input
 *   label="Email"
 *   placeholder="Enter your email"
 *   type="email"
 *   required
 * />
 *
 * <Input
 *   label="Search"
 *   leftIcon={<SearchIcon />}
 *   placeholder="Search..."
 * />
 *
 * <Input
 *   label="Password"
 *   type="password"
 *   error="Password must be at least 8 characters"
 * />
 * ```
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      size = 'md',
      leftIcon,
      rightIcon,
      required,
      wrapperClassName = '',
      className = '',
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    const baseInputStyles = [
      'block w-full rounded-lg',
      'bg-white dark:bg-dark-card',
      'border transition-colors duration-200',
      'placeholder:text-slate-400 dark:placeholder:text-slate-500',
      'focus:outline-none focus:ring-2 focus:ring-offset-0',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-slate-50 dark:disabled:bg-slate-800',
    ].join(' ');

    const stateStyles = error
      ? 'border-red-300 dark:border-red-500 text-red-900 dark:text-red-100 focus:border-red-500 focus:ring-red-500/20'
      : 'border-slate-300 dark:border-dark-border text-slate-900 dark:text-slate-100 focus:border-brand-500 focus:ring-brand-500/20';

    const paddingStyles = [
      sizeStyles[size],
      leftIcon ? leftPaddingStyles[size] : '',
      rightIcon ? rightPaddingStyles[size] : '',
    ]
      .filter(Boolean)
      .join(' ');

    const inputClassName = [baseInputStyles, stateStyles, paddingStyles, className]
      .filter(Boolean)
      .join(' ');

    return (
      <div className={`w-full ${wrapperClassName}`}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
          >
            {label}
            {required && (
              <span className="text-red-500 ml-1" aria-hidden="true">
                *
              </span>
            )}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div
              className={`absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 pointer-events-none ${iconSizeStyles[size]}`}
              aria-hidden="true"
            >
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            disabled={disabled}
            className={inputClassName}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={
              error
                ? `${inputId}-error`
                : helperText
                ? `${inputId}-helper`
                : undefined
            }
            aria-required={required}
            {...props}
          />
          {rightIcon && (
            <div
              className={`absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 ${iconSizeStyles[size]}`}
              aria-hidden="true"
            >
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p
            id={`${inputId}-error`}
            className="mt-1.5 text-sm text-red-600 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}
        {!error && helperText && (
          <p
            id={`${inputId}-helper`}
            className="mt-1.5 text-sm text-slate-500 dark:text-slate-400"
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
