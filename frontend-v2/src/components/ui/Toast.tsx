import {
  forwardRef,
  useState,
  useEffect,
  useCallback,
  createContext,
  useContext,
  type HTMLAttributes,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';

export type ToastVariant = 'default' | 'success' | 'warning' | 'error' | 'info';
export type ToastPosition = 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';

export interface ToastProps extends HTMLAttributes<HTMLDivElement> {
  /** Unique identifier for the toast */
  id?: string;
  /** The visual style variant */
  variant?: ToastVariant;
  /** Title of the toast */
  title?: string;
  /** Description/message of the toast */
  description?: ReactNode;
  /** Duration in milliseconds before auto-close (0 to disable) */
  duration?: number;
  /** Whether the toast can be dismissed */
  dismissible?: boolean;
  /** Callback when the toast is closed */
  onClose?: () => void;
  /** Icon to display */
  icon?: ReactNode;
  /** Action button */
  action?: {
    label: string;
    onClick: () => void;
  };
  /** Additional CSS classes */
  className?: string;
}

const variantStyles: Record<ToastVariant, { bg: string; icon: string; border: string }> = {
  default: {
    bg: 'bg-white dark:bg-dark-card',
    icon: 'text-slate-500',
    border: 'border-slate-200 dark:border-dark-border',
  },
  success: {
    bg: 'bg-white dark:bg-dark-card',
    icon: 'text-green-500',
    border: 'border-green-200 dark:border-green-800',
  },
  warning: {
    bg: 'bg-white dark:bg-dark-card',
    icon: 'text-amber-500',
    border: 'border-amber-200 dark:border-amber-800',
  },
  error: {
    bg: 'bg-white dark:bg-dark-card',
    icon: 'text-red-500',
    border: 'border-red-200 dark:border-red-800',
  },
  info: {
    bg: 'bg-white dark:bg-dark-card',
    icon: 'text-blue-500',
    border: 'border-blue-200 dark:border-blue-800',
  },
};

const defaultIcons: Record<ToastVariant, ReactNode> = {
  default: null,
  success: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  ),
  warning: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  error: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  info: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

/**
 * Individual Toast component.
 */
export const Toast = forwardRef<HTMLDivElement, ToastProps>(
  (
    {
      variant = 'default',
      title,
      description,
      duration = 5000,
      dismissible = true,
      onClose,
      icon,
      action,
      className = '',
      ...props
    },
    ref
  ) => {
    const [isExiting, setIsExiting] = useState(false);
    const styles = variantStyles[variant];
    const displayIcon = icon ?? defaultIcons[variant];

    const handleClose = useCallback(() => {
      setIsExiting(true);
      setTimeout(() => {
        onClose?.();
      }, 200);
    }, [onClose]);

    useEffect(() => {
      if (duration > 0) {
        const timer = setTimeout(handleClose, duration);
        return () => clearTimeout(timer);
      }
    }, [duration, handleClose]);

    return (
      <div
        ref={ref}
        role="alert"
        aria-live="polite"
        className={`
          ${styles.bg} ${styles.border}
          w-full max-w-sm rounded-lg border shadow-lg
          pointer-events-auto
          ${isExiting ? 'animate-fade-out' : 'animate-slide-in'}
          ${className}
        `}
        {...props}
      >
        <div className="flex items-start gap-3 p-4">
          {displayIcon && (
            <div className={`flex-shrink-0 ${styles.icon}`} aria-hidden="true">
              {displayIcon}
            </div>
          )}
          <div className="flex-1 min-w-0">
            {title && (
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {title}
              </p>
            )}
            {description && (
              <p className={`text-sm text-slate-600 dark:text-slate-400 ${title ? 'mt-1' : ''}`}>
                {description}
              </p>
            )}
            {action && (
              <button
                type="button"
                onClick={action.onClick}
                className="mt-2 text-sm font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400 dark:hover:text-brand-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                {action.label}
              </button>
            )}
          </div>
          {dismissible && (
            <button
              type="button"
              onClick={handleClose}
              className="flex-shrink-0 p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:text-slate-300 dark:hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 transition-colors"
              aria-label="Dismiss"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>
    );
  }
);

Toast.displayName = 'Toast';

// Toast Context for managing toasts globally
interface ToastItem extends ToastProps {
  id: string;
}

interface ToastContextValue {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastProps, 'id'>) => string;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

interface ToastProviderProps {
  children: ReactNode;
  position?: ToastPosition;
  maxToasts?: number;
}

const positionStyles: Record<ToastPosition, string> = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-center': 'top-4 left-1/2 -translate-x-1/2',
  'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
};

/**
 * Toast Provider component for managing toasts globally.
 *
 * @example
 * ```tsx
 * // In App.tsx
 * <ToastProvider position="top-right">
 *   <App />
 * </ToastProvider>
 *
 * // In any component
 * function MyComponent() {
 *   const { addToast } = useToast();
 *
 *   const showSuccess = () => {
 *     addToast({
 *       variant: 'success',
 *       title: 'Success!',
 *       description: 'Your action was completed.',
 *     });
 *   };
 * }
 * ```
 */
export function ToastProvider({
  children,
  position = 'top-right',
  maxToasts = 5,
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback(
    (toast: Omit<ToastProps, 'id'>) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      setToasts((prev) => {
        const newToasts = [...prev, { ...toast, id }];
        if (newToasts.length > maxToasts) {
          return newToasts.slice(-maxToasts);
        }
        return newToasts;
      });
      return id;
    },
    [maxToasts]
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const clearToasts = useCallback(() => {
    setToasts([]);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, clearToasts }}>
      {children}
      {createPortal(
        <div
          className={`fixed z-[500] flex flex-col gap-2 pointer-events-none ${positionStyles[position]}`}
          aria-live="polite"
          aria-label="Notifications"
        >
          {toasts.map((toast) => (
            <Toast
              key={toast.id}
              {...toast}
              onClose={() => removeToast(toast.id)}
            />
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}

export default Toast;
