import {
  forwardRef,
  useState,
  createContext,
  useContext,
  type HTMLAttributes,
  type ReactNode,
  type KeyboardEvent,
} from 'react';

export type TabsVariant = 'default' | 'pills' | 'underline';
export type TabsSize = 'sm' | 'md' | 'lg';

export interface TabsProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onChange'> {
  /** The currently active tab value */
  value?: string;
  /** Default active tab value (uncontrolled) */
  defaultValue?: string;
  /** Callback when tab changes */
  onChange?: (value: string) => void;
  /** Visual variant of the tabs */
  variant?: TabsVariant;
  /** Size of the tabs */
  size?: TabsSize;
  /** Whether tabs should take full width */
  fullWidth?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Tab content */
  children?: ReactNode;
}

export interface TabListProps extends HTMLAttributes<HTMLDivElement> {
  /** Additional CSS classes */
  className?: string;
  /** Tab list content */
  children?: ReactNode;
}

export interface TabProps extends HTMLAttributes<HTMLButtonElement> {
  /** Unique value for this tab */
  value: string;
  /** Whether the tab is disabled */
  disabled?: boolean;
  /** Icon to display before the label */
  icon?: ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Tab label */
  children?: ReactNode;
}

export interface TabPanelProps extends HTMLAttributes<HTMLDivElement> {
  /** Value that matches the associated tab */
  value: string;
  /** Additional CSS classes */
  className?: string;
  /** Panel content */
  children?: ReactNode;
}

// Context for sharing state between Tabs components
interface TabsContextValue {
  activeValue: string;
  setActiveValue: (value: string) => void;
  variant: TabsVariant;
  size: TabsSize;
  fullWidth: boolean;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('Tab components must be used within a Tabs component');
  }
  return context;
}

const variantStyles: Record<TabsVariant, { list: string; tab: string; active: string }> = {
  default: {
    list: 'border-b border-slate-200 dark:border-dark-border',
    tab: 'border-b-2 border-transparent -mb-px',
    active: 'border-brand-500 text-brand-600 dark:text-brand-400',
  },
  pills: {
    list: 'gap-2',
    tab: 'rounded-lg',
    active: 'bg-brand-500 text-white shadow-sm',
  },
  underline: {
    list: 'gap-4',
    tab: 'border-b-2 border-transparent',
    active: 'border-brand-500 text-brand-600 dark:text-brand-400',
  },
};

const sizeStyles: Record<TabsSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
};

/**
 * Tabs component for organizing content into separate views.
 *
 * @example
 * ```tsx
 * <Tabs defaultValue="tab1" variant="default">
 *   <TabList>
 *     <Tab value="tab1">Tab 1</Tab>
 *     <Tab value="tab2">Tab 2</Tab>
 *     <Tab value="tab3" disabled>Tab 3</Tab>
 *   </TabList>
 *   <TabPanel value="tab1">Content for Tab 1</TabPanel>
 *   <TabPanel value="tab2">Content for Tab 2</TabPanel>
 *   <TabPanel value="tab3">Content for Tab 3</TabPanel>
 * </Tabs>
 * ```
 */
export const Tabs = forwardRef<HTMLDivElement, TabsProps>(
  (
    {
      value,
      defaultValue = '',
      onChange,
      variant = 'default',
      size = 'md',
      fullWidth = false,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const [internalValue, setInternalValue] = useState(defaultValue);
    const activeValue = value ?? internalValue;

    const setActiveValue = (newValue: string) => {
      if (value === undefined) {
        setInternalValue(newValue);
      }
      onChange?.(newValue);
    };

    return (
      <TabsContext.Provider
        value={{ activeValue, setActiveValue, variant, size, fullWidth }}
      >
        <div ref={ref} className={className} {...props}>
          {children}
        </div>
      </TabsContext.Provider>
    );
  }
);

Tabs.displayName = 'Tabs';

/**
 * TabList component for containing tabs.
 */
export const TabList = forwardRef<HTMLDivElement, TabListProps>(
  ({ className = '', children, ...props }, ref) => {
    const { variant, fullWidth } = useTabsContext();
    const styles = variantStyles[variant];

    const baseStyles = 'flex items-center';
    const widthStyles = fullWidth ? 'w-full' : '';

    return (
      <div
        ref={ref}
        role="tablist"
        className={`${baseStyles} ${styles.list} ${widthStyles} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

TabList.displayName = 'TabList';

/**
 * Tab component for individual tab buttons.
 */
export const Tab = forwardRef<HTMLButtonElement, TabProps>(
  ({ value, disabled = false, icon, className = '', children, ...props }, ref) => {
    const { activeValue, setActiveValue, variant, size, fullWidth } = useTabsContext();
    const isActive = activeValue === value;
    const styles = variantStyles[variant];

    const baseStyles = [
      'inline-flex items-center justify-center gap-2',
      'font-medium',
      'transition-all duration-200',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2',
      'dark:focus-visible:ring-offset-dark-bg',
      'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' ');

    const inactiveStyles =
      'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200';
    const widthStyles = fullWidth ? 'flex-1' : '';

    const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
      const tabs = event.currentTarget.parentElement?.querySelectorAll('[role="tab"]:not([disabled])');
      if (!tabs) return;

      const tabArray = Array.from(tabs) as HTMLButtonElement[];
      const currentIndex = tabArray.indexOf(event.currentTarget);

      let nextIndex: number | null = null;

      switch (event.key) {
        case 'ArrowLeft':
          nextIndex = currentIndex > 0 ? currentIndex - 1 : tabArray.length - 1;
          break;
        case 'ArrowRight':
          nextIndex = currentIndex < tabArray.length - 1 ? currentIndex + 1 : 0;
          break;
        case 'Home':
          nextIndex = 0;
          break;
        case 'End':
          nextIndex = tabArray.length - 1;
          break;
      }

      if (nextIndex !== null) {
        event.preventDefault();
        tabArray[nextIndex].focus();
      }
    };

    return (
      <button
        ref={ref}
        type="button"
        role="tab"
        aria-selected={isActive}
        aria-controls={`tabpanel-${value}`}
        id={`tab-${value}`}
        tabIndex={isActive ? 0 : -1}
        disabled={disabled}
        onClick={() => setActiveValue(value)}
        onKeyDown={handleKeyDown}
        className={`
          ${baseStyles}
          ${sizeStyles[size]}
          ${styles.tab}
          ${isActive ? styles.active : inactiveStyles}
          ${widthStyles}
          ${className}
        `}
        {...props}
      >
        {icon && <span className="flex-shrink-0" aria-hidden="true">{icon}</span>}
        {children}
      </button>
    );
  }
);

Tab.displayName = 'Tab';

/**
 * TabPanel component for tab content.
 */
export const TabPanel = forwardRef<HTMLDivElement, TabPanelProps>(
  ({ value, className = '', children, ...props }, ref) => {
    const { activeValue } = useTabsContext();
    const isActive = activeValue === value;

    if (!isActive) return null;

    return (
      <div
        ref={ref}
        role="tabpanel"
        id={`tabpanel-${value}`}
        aria-labelledby={`tab-${value}`}
        tabIndex={0}
        className={`mt-4 focus:outline-none ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

TabPanel.displayName = 'TabPanel';

export default Tabs;
