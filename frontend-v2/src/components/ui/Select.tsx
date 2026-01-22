import {
  forwardRef,
  useState,
  useRef,
  useEffect,
  useCallback,
  type HTMLAttributes,
  type ReactNode,
  type KeyboardEvent,
} from 'react';

export type SelectSize = 'sm' | 'md' | 'lg';

export interface SelectOption {
  /** Unique value for the option */
  value: string;
  /** Display label for the option */
  label: string;
  /** Whether the option is disabled */
  disabled?: boolean;
  /** Optional icon */
  icon?: ReactNode;
}

export interface SelectProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onChange'> {
  /** Array of options */
  options: SelectOption[];
  /** Currently selected value */
  value?: string;
  /** Placeholder text when no option is selected */
  placeholder?: string;
  /** Label for the select */
  label?: string;
  /** Error message */
  error?: string;
  /** Helper text */
  helperText?: string;
  /** Size of the select */
  size?: SelectSize;
  /** Whether the select is disabled */
  disabled?: boolean;
  /** Whether the select is required */
  required?: boolean;
  /** Callback when selection changes */
  onChange?: (value: string) => void;
  /** Additional CSS classes */
  className?: string;
}

const sizeStyles: Record<SelectSize, { button: string; option: string }> = {
  sm: {
    button: 'px-3 py-1.5 text-sm',
    option: 'px-3 py-1.5 text-sm',
  },
  md: {
    button: 'px-3 py-2 text-base',
    option: 'px-3 py-2 text-base',
  },
  lg: {
    button: 'px-4 py-3 text-lg',
    option: 'px-4 py-3 text-lg',
  },
};

/**
 * Select dropdown component with keyboard navigation and accessibility support.
 *
 * @example
 * ```tsx
 * const options = [
 *   { value: 'option1', label: 'Option 1' },
 *   { value: 'option2', label: 'Option 2' },
 *   { value: 'option3', label: 'Option 3', disabled: true },
 * ];
 *
 * <Select
 *   label="Choose an option"
 *   options={options}
 *   value={selected}
 *   onChange={setSelected}
 *   placeholder="Select..."
 * />
 * ```
 */
export const Select = forwardRef<HTMLDivElement, SelectProps>(
  (
    {
      options,
      value,
      placeholder = 'Select...',
      label,
      error,
      helperText,
      size = 'md',
      disabled = false,
      required = false,
      onChange,
      className = '',
      ...props
    },
    ref
  ) => {
    const [isOpen, setIsOpen] = useState(false);
    const [highlightedIndex, setHighlightedIndex] = useState(-1);
    const containerRef = useRef<HTMLDivElement>(null);
    const listboxRef = useRef<HTMLUListElement>(null);
    const buttonRef = useRef<HTMLButtonElement>(null);

    const selectedOption = options.find((opt) => opt.value === value);
    const selectId = label?.toLowerCase().replace(/\s+/g, '-') || 'select';
    const styles = sizeStyles[size];

    // Close dropdown when clicking outside
    useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
          setIsOpen(false);
        }
      };

      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Reset highlighted index when dropdown opens
    useEffect(() => {
      if (isOpen) {
        const selectedIndex = options.findIndex((opt) => opt.value === value);
        setHighlightedIndex(selectedIndex >= 0 ? selectedIndex : 0);
      }
    }, [isOpen, options, value]);

    // Scroll highlighted option into view
    useEffect(() => {
      if (isOpen && highlightedIndex >= 0 && listboxRef.current) {
        const option = listboxRef.current.children[highlightedIndex] as HTMLElement;
        option?.scrollIntoView({ block: 'nearest' });
      }
    }, [highlightedIndex, isOpen]);

    const handleSelect = useCallback(
      (optionValue: string) => {
        const option = options.find((opt) => opt.value === optionValue);
        if (option && !option.disabled) {
          onChange?.(optionValue);
          setIsOpen(false);
          buttonRef.current?.focus();
        }
      },
      [onChange, options]
    );

    const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
      if (disabled) return;

      switch (event.key) {
        case 'Enter':
        case ' ':
          event.preventDefault();
          if (isOpen && highlightedIndex >= 0) {
            handleSelect(options[highlightedIndex].value);
          } else {
            setIsOpen(true);
          }
          break;
        case 'ArrowDown':
          event.preventDefault();
          if (!isOpen) {
            setIsOpen(true);
          } else {
            setHighlightedIndex((prev) => {
              let next = prev + 1;
              while (next < options.length && options[next].disabled) next++;
              return next < options.length ? next : prev;
            });
          }
          break;
        case 'ArrowUp':
          event.preventDefault();
          if (!isOpen) {
            setIsOpen(true);
          } else {
            setHighlightedIndex((prev) => {
              let next = prev - 1;
              while (next >= 0 && options[next].disabled) next--;
              return next >= 0 ? next : prev;
            });
          }
          break;
        case 'Home':
          event.preventDefault();
          if (isOpen) {
            const firstEnabled = options.findIndex((opt) => !opt.disabled);
            setHighlightedIndex(firstEnabled);
          }
          break;
        case 'End':
          event.preventDefault();
          if (isOpen) {
            const lastEnabled = options.reduce((acc, opt, idx) => (!opt.disabled ? idx : acc), -1);
            setHighlightedIndex(lastEnabled);
          }
          break;
        case 'Escape':
          event.preventDefault();
          setIsOpen(false);
          break;
        case 'Tab':
          setIsOpen(false);
          break;
      }
    };

    const buttonStateStyles = error
      ? 'border-red-300 dark:border-red-500 focus:border-red-500 focus:ring-red-500/20'
      : 'border-slate-300 dark:border-dark-border focus:border-brand-500 focus:ring-brand-500/20';

    return (
      <div ref={ref} className={`w-full ${className}`} {...props}>
        {label && (
          <label
            htmlFor={selectId}
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
        <div ref={containerRef} className="relative">
          <button
            ref={buttonRef}
            type="button"
            id={selectId}
            role="combobox"
            aria-expanded={isOpen}
            aria-haspopup="listbox"
            aria-controls={`${selectId}-listbox`}
            aria-labelledby={label ? `${selectId}-label` : undefined}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={
              error ? `${selectId}-error` : helperText ? `${selectId}-helper` : undefined
            }
            aria-required={required}
            disabled={disabled}
            onClick={() => !disabled && setIsOpen(!isOpen)}
            onKeyDown={handleKeyDown}
            className={`
              w-full flex items-center justify-between gap-2
              bg-white dark:bg-dark-card
              border rounded-lg
              text-left
              transition-colors duration-200
              focus:outline-none focus:ring-2 focus:ring-offset-0
              disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-slate-50 dark:disabled:bg-slate-800
              ${styles.button}
              ${buttonStateStyles}
            `}
          >
            <span
              className={`truncate ${
                selectedOption
                  ? 'text-slate-900 dark:text-slate-100'
                  : 'text-slate-400 dark:text-slate-500'
              }`}
            >
              {selectedOption ? (
                <span className="flex items-center gap-2">
                  {selectedOption.icon && (
                    <span className="flex-shrink-0" aria-hidden="true">
                      {selectedOption.icon}
                    </span>
                  )}
                  {selectedOption.label}
                </span>
              ) : (
                placeholder
              )}
            </span>
            <svg
              className={`w-5 h-5 flex-shrink-0 text-slate-400 transition-transform duration-200 ${
                isOpen ? 'rotate-180' : ''
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {isOpen && (
            <ul
              ref={listboxRef}
              role="listbox"
              id={`${selectId}-listbox`}
              aria-labelledby={selectId}
              className={`
                absolute z-50 w-full mt-1
                bg-white dark:bg-dark-card
                border border-slate-200 dark:border-dark-border
                rounded-lg shadow-lg
                max-h-60 overflow-auto
                py-1
                animate-scale-in origin-top
              `}
            >
              {options.map((option, index) => {
                const isSelected = option.value === value;
                const isHighlighted = index === highlightedIndex;

                return (
                  <li
                    key={option.value}
                    role="option"
                    aria-selected={isSelected}
                    aria-disabled={option.disabled}
                    onClick={() => handleSelect(option.value)}
                    onMouseEnter={() => !option.disabled && setHighlightedIndex(index)}
                    className={`
                      flex items-center gap-2 cursor-pointer
                      ${styles.option}
                      ${
                        option.disabled
                          ? 'opacity-50 cursor-not-allowed text-slate-400'
                          : isHighlighted
                          ? 'bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-300'
                          : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                      }
                    `}
                  >
                    {option.icon && (
                      <span className="flex-shrink-0" aria-hidden="true">
                        {option.icon}
                      </span>
                    )}
                    <span className="flex-1 truncate">{option.label}</span>
                    {isSelected && (
                      <svg
                        className="w-5 h-5 flex-shrink-0 text-brand-500"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                        aria-hidden="true"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        {error && (
          <p
            id={`${selectId}-error`}
            className="mt-1.5 text-sm text-red-600 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}
        {!error && helperText && (
          <p
            id={`${selectId}-helper`}
            className="mt-1.5 text-sm text-slate-500 dark:text-slate-400"
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export default Select;
