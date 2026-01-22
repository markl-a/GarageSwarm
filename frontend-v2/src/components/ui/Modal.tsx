import {
  forwardRef,
  useEffect,
  useCallback,
  type HTMLAttributes,
  type ReactNode,
  type MouseEvent,
} from 'react';
import { createPortal } from 'react-dom';

export type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';

export interface ModalProps extends HTMLAttributes<HTMLDivElement> {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback when the modal should close */
  onClose: () => void;
  /** Title of the modal */
  title?: ReactNode;
  /** Description/subtitle of the modal */
  description?: ReactNode;
  /** Size of the modal */
  size?: ModalSize;
  /** Whether to close on overlay click */
  closeOnOverlayClick?: boolean;
  /** Whether to close on Escape key press */
  closeOnEscape?: boolean;
  /** Whether to show the close button */
  showCloseButton?: boolean;
  /** Footer content */
  footer?: ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Modal content */
  children?: ReactNode;
}

const sizeStyles: Record<ModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-4xl',
};

/**
 * Modal dialog component with overlay and accessibility support.
 *
 * @example
 * ```tsx
 * const [isOpen, setIsOpen] = useState(false);
 *
 * <Modal
 *   isOpen={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   title="Confirm Action"
 *   description="Are you sure you want to proceed?"
 *   footer={
 *     <>
 *       <Button variant="ghost" onClick={() => setIsOpen(false)}>
 *         Cancel
 *       </Button>
 *       <Button variant="primary" onClick={handleConfirm}>
 *         Confirm
 *       </Button>
 *     </>
 *   }
 * >
 *   Modal content goes here
 * </Modal>
 * ```
 */
export const Modal = forwardRef<HTMLDivElement, ModalProps>(
  (
    {
      isOpen,
      onClose,
      title,
      description,
      size = 'md',
      closeOnOverlayClick = true,
      closeOnEscape = true,
      showCloseButton = true,
      footer,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    // Handle Escape key press
    const handleEscape = useCallback(
      (event: KeyboardEvent) => {
        if (closeOnEscape && event.key === 'Escape') {
          onClose();
        }
      },
      [closeOnEscape, onClose]
    );

    // Handle overlay click
    const handleOverlayClick = (event: MouseEvent<HTMLDivElement>) => {
      if (closeOnOverlayClick && event.target === event.currentTarget) {
        onClose();
      }
    };

    // Add/remove escape key listener
    useEffect(() => {
      if (isOpen) {
        document.addEventListener('keydown', handleEscape);
        document.body.style.overflow = 'hidden';
      }

      return () => {
        document.removeEventListener('keydown', handleEscape);
        document.body.style.overflow = '';
      };
    }, [isOpen, handleEscape]);

    if (!isOpen) return null;

    const modalContent = (
      <div
        className="fixed inset-0 z-[200] overflow-y-auto"
        aria-labelledby={title ? 'modal-title' : undefined}
        aria-describedby={description ? 'modal-description' : undefined}
        role="dialog"
        aria-modal="true"
      >
        {/* Overlay */}
        <div
          className="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm transition-opacity animate-fade-in"
          aria-hidden="true"
          onClick={handleOverlayClick}
        />

        {/* Modal positioning wrapper */}
        <div
          className="flex min-h-full items-center justify-center p-4"
          onClick={handleOverlayClick}
        >
          {/* Modal panel */}
          <div
            ref={ref}
            className={`
              relative w-full ${sizeStyles[size]}
              bg-white dark:bg-dark-card
              rounded-xl shadow-xl
              border border-slate-200 dark:border-dark-border
              transform transition-all animate-scale-in
              ${className}
            `}
            {...props}
          >
            {/* Header */}
            {(title || showCloseButton) && (
              <div className="flex items-start justify-between gap-4 px-6 pt-6 pb-4">
                <div className="flex-1 min-w-0">
                  {title && (
                    <h2
                      id="modal-title"
                      className="text-lg font-semibold text-slate-900 dark:text-slate-100"
                    >
                      {title}
                    </h2>
                  )}
                  {description && (
                    <p
                      id="modal-description"
                      className="mt-1 text-sm text-slate-500 dark:text-slate-400"
                    >
                      {description}
                    </p>
                  )}
                </div>
                {showCloseButton && (
                  <button
                    type="button"
                    onClick={onClose}
                    className="flex-shrink-0 p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:text-slate-300 dark:hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 transition-colors"
                    aria-label="Close modal"
                  >
                    <svg
                      className="w-5 h-5"
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
              </div>
            )}

            {/* Content */}
            <div className="px-6 pb-6">{children}</div>

            {/* Footer */}
            {footer && (
              <div className="flex items-center justify-end gap-3 px-6 py-4 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-dark-border rounded-b-xl">
                {footer}
              </div>
            )}
          </div>
        </div>
      </div>
    );

    // Render in portal
    return createPortal(modalContent, document.body);
  }
);

Modal.displayName = 'Modal';

export default Modal;
