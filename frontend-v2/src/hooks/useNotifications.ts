/**
 * useNotifications Hook
 *
 * Hook for managing notifications with toast support and real-time updates.
 * Integrates with the notification store and WebSocket service.
 */

import { useEffect, useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import websocketService from '../services/websocket';
import { useWebSocketChannels } from './useWebSocket';
import {
  useNotificationStore,
  NotificationInput,
  selectUnreadCount,
  selectUnreadNotifications,
  selectToastSettings,
} from '../stores/notificationStore';
import {
  WS_EVENTS,
  Notification,
  NotificationPayload,
  NotificationCategory,
  NotificationType,
} from '../types/websocket';

// ============================================================================
// Types
// ============================================================================

export interface ToastNotification {
  id: string;
  notification: Notification;
  visible: boolean;
  exiting: boolean;
}

export interface UseNotificationsOptions {
  /** Enable toast notifications */
  enableToasts?: boolean;
  /** Custom toast duration (overrides store setting) */
  toastDuration?: number;
  /** Maximum number of visible toasts */
  maxVisibleToasts?: number;
  /** Auto dismiss toasts */
  autoDismiss?: boolean;
  /** Categories to show toasts for (all if not specified) */
  toastCategories?: NotificationCategory[];
  /** Types to show toasts for (all if not specified) */
  toastTypes?: NotificationType[];
  /** Callback when notification is clicked */
  onNotificationClick?: (notification: Notification) => void;
  /** Enable the hook */
  enabled?: boolean;
}

export interface UseNotificationsReturn {
  /** All notifications */
  notifications: Notification[];
  /** Unread notifications */
  unreadNotifications: Notification[];
  /** Unread count */
  unreadCount: number;
  /** Active toast notifications */
  toasts: ToastNotification[];
  /** Whether the notification center is open */
  isOpen: boolean;
  /** Open the notification center */
  open: () => void;
  /** Close the notification center */
  close: () => void;
  /** Toggle the notification center */
  toggle: () => void;
  /** Add a notification */
  addNotification: (input: NotificationInput) => Notification;
  /** Mark a notification as read */
  markAsRead: (notificationId: string) => void;
  /** Mark all notifications as read */
  markAllAsRead: () => void;
  /** Remove a notification */
  removeNotification: (notificationId: string) => void;
  /** Clear all notifications */
  clearAll: () => void;
  /** Dismiss a toast */
  dismissToast: (toastId: string) => void;
  /** Dismiss all toasts */
  dismissAllToasts: () => void;
  /** Navigate to notification link */
  navigateToNotification: (notification: Notification) => void;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useNotifications(
  options: UseNotificationsOptions = {}
): UseNotificationsReturn {
  const {
    enableToasts = true,
    toastDuration: customToastDuration,
    maxVisibleToasts = 5,
    autoDismiss = true,
    toastCategories,
    toastTypes,
    onNotificationClick,
    enabled = true,
  } = options;

  const navigate = useNavigate();

  // Store state
  const notifications = useNotificationStore((state) => state.notifications);
  const unreadNotifications = useNotificationStore(selectUnreadNotifications);
  const unreadCount = useNotificationStore(selectUnreadCount);
  const storeToastSettings = useNotificationStore(selectToastSettings);
  const storeAddNotification = useNotificationStore((state) => state.addNotification);
  const storeMarkAsRead = useNotificationStore((state) => state.markAsRead);
  const storeMarkAllAsRead = useNotificationStore((state) => state.markAllAsRead);
  const storeRemoveNotification = useNotificationStore(
    (state) => state.removeNotification
  );
  const storeClearAll = useNotificationStore((state) => state.clearAll);

  // Local state
  const [isOpen, setIsOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  // Refs for timeouts
  const toastTimeouts = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map()
  );

  // Computed toast duration
  const toastDuration = customToastDuration ?? storeToastSettings.toastDuration;

  // Subscribe to notifications channel
  useWebSocketChannels('notifications', enabled);

  // ============================================================================
  // Toast Management
  // ============================================================================

  const addToast = useCallback(
    (notification: Notification) => {
      // Check if toasts are enabled
      if (!enableToasts || !storeToastSettings.showToasts) return;

      // Check category filter
      if (toastCategories && !toastCategories.includes(notification.category)) {
        return;
      }

      // Check type filter
      if (toastTypes && !toastTypes.includes(notification.type)) {
        return;
      }

      const toastId = `toast_${notification.id}`;

      setToasts((prev) => {
        // Check if already exists
        if (prev.some((t) => t.id === toastId)) {
          return prev;
        }

        const newToast: ToastNotification = {
          id: toastId,
          notification,
          visible: true,
          exiting: false,
        };

        // Add new toast and limit to max
        const updated = [newToast, ...prev].slice(0, maxVisibleToasts);

        return updated;
      });

      // Auto dismiss
      if (autoDismiss) {
        const timeoutId = setTimeout(() => {
          dismissToast(toastId);
        }, toastDuration);

        toastTimeouts.current.set(toastId, timeoutId);
      }
    },
    [
      enableToasts,
      storeToastSettings.showToasts,
      toastCategories,
      toastTypes,
      maxVisibleToasts,
      autoDismiss,
      toastDuration,
    ]
  );

  const dismissToast = useCallback((toastId: string) => {
    // Clear timeout if exists
    const timeout = toastTimeouts.current.get(toastId);
    if (timeout) {
      clearTimeout(timeout);
      toastTimeouts.current.delete(toastId);
    }

    // Start exit animation
    setToasts((prev) =>
      prev.map((t) => (t.id === toastId ? { ...t, exiting: true } : t))
    );

    // Remove after animation
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== toastId));
    }, 300); // Animation duration
  }, []);

  const dismissAllToasts = useCallback(() => {
    // Clear all timeouts
    toastTimeouts.current.forEach((timeout) => clearTimeout(timeout));
    toastTimeouts.current.clear();

    // Start exit animation for all
    setToasts((prev) => prev.map((t) => ({ ...t, exiting: true })));

    // Remove all after animation
    setTimeout(() => {
      setToasts([]);
    }, 300);
  }, []);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      toastTimeouts.current.forEach((timeout) => clearTimeout(timeout));
    };
  }, []);

  // ============================================================================
  // WebSocket Event Handler
  // ============================================================================

  useEffect(() => {
    if (!enabled) return;

    const unsubscribe = websocketService.on(
      WS_EVENTS.NOTIFICATION,
      (payload: NotificationPayload) => {
        // Notification is already added by the server, just show toast
        addToast(payload.notification);
      }
    );

    return unsubscribe;
  }, [enabled, addToast]);

  // ============================================================================
  // Actions
  // ============================================================================

  const addNotification = useCallback(
    (input: NotificationInput): Notification => {
      const notification = storeAddNotification(input);
      addToast(notification);
      return notification;
    },
    [storeAddNotification, addToast]
  );

  const markAsRead = useCallback(
    (notificationId: string) => {
      storeMarkAsRead(notificationId);
    },
    [storeMarkAsRead]
  );

  const markAllAsRead = useCallback(() => {
    storeMarkAllAsRead();
  }, [storeMarkAllAsRead]);

  const removeNotification = useCallback(
    (notificationId: string) => {
      storeRemoveNotification(notificationId);
    },
    [storeRemoveNotification]
  );

  const clearAll = useCallback(() => {
    storeClearAll();
    dismissAllToasts();
  }, [storeClearAll, dismissAllToasts]);

  const open = useCallback(() => {
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  const toggle = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const navigateToNotification = useCallback(
    (notification: Notification) => {
      // Mark as read
      markAsRead(notification.id);

      // Close notification center
      close();

      // Custom click handler
      if (onNotificationClick) {
        onNotificationClick(notification);
        return;
      }

      // Navigate to link if provided
      if (notification.link) {
        navigate(notification.link);
      }
    },
    [markAsRead, close, onNotificationClick, navigate]
  );

  return {
    notifications,
    unreadNotifications,
    unreadCount,
    toasts,
    isOpen,
    open,
    close,
    toggle,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    dismissToast,
    dismissAllToasts,
    navigateToNotification,
  };
}

// ============================================================================
// Specialized Hooks
// ============================================================================

/**
 * Hook for just unread count
 */
export function useUnreadCount(): number {
  return useNotificationStore(selectUnreadCount);
}

/**
 * Hook for checking if there are unread notifications
 */
export function useHasUnreadNotifications(): boolean {
  const count = useNotificationStore(selectUnreadCount);
  return count > 0;
}

/**
 * Hook for notification center open state
 */
export function useNotificationCenterState(): {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
} {
  const [isOpen, setIsOpen] = useState(false);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return { isOpen, open, close, toggle };
}

/**
 * Hook for toast notifications only
 */
export function useToastNotifications(
  options: Pick<
    UseNotificationsOptions,
    | 'enableToasts'
    | 'toastDuration'
    | 'maxVisibleToasts'
    | 'autoDismiss'
    | 'toastCategories'
    | 'toastTypes'
  > = {}
): {
  toasts: ToastNotification[];
  dismissToast: (toastId: string) => void;
  dismissAllToasts: () => void;
} {
  const { toasts, dismissToast, dismissAllToasts } = useNotifications({
    ...options,
    enabled: true,
  });

  return { toasts, dismissToast, dismissAllToasts };
}

/**
 * Hook for programmatic notification creation
 */
export function useNotificationActions(): {
  addNotification: (input: NotificationInput) => Notification;
  success: (title: string, message: string, link?: string) => Notification;
  error: (title: string, message: string, link?: string) => Notification;
  warning: (title: string, message: string, link?: string) => Notification;
  info: (title: string, message: string, link?: string) => Notification;
} {
  const addNotification = useNotificationStore((state) => state.addNotification);

  const success = useCallback(
    (title: string, message: string, link?: string): Notification =>
      addNotification({
        type: NotificationType.SUCCESS,
        category: NotificationCategory.SYSTEM,
        title,
        message,
        link,
      }),
    [addNotification]
  );

  const error = useCallback(
    (title: string, message: string, link?: string): Notification =>
      addNotification({
        type: NotificationType.ERROR,
        category: NotificationCategory.SYSTEM,
        title,
        message,
        link,
      }),
    [addNotification]
  );

  const warning = useCallback(
    (title: string, message: string, link?: string): Notification =>
      addNotification({
        type: NotificationType.WARNING,
        category: NotificationCategory.SYSTEM,
        title,
        message,
        link,
      }),
    [addNotification]
  );

  const info = useCallback(
    (title: string, message: string, link?: string): Notification =>
      addNotification({
        type: NotificationType.INFO,
        category: NotificationCategory.SYSTEM,
        title,
        message,
        link,
      }),
    [addNotification]
  );

  return {
    addNotification,
    success,
    error,
    warning,
    info,
  };
}

export default useNotifications;
