/**
 * Notification Store
 *
 * Zustand store for managing application notifications.
 * Handles notification list, unread count, and persistence.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import {
  Notification,
  NotificationType,
  NotificationCategory,
} from '../types/websocket';

// ============================================================================
// Types
// ============================================================================

export interface NotificationInput {
  type: NotificationType;
  category: NotificationCategory;
  title: string;
  message: string;
  data?: Record<string, unknown>;
  link?: string;
}

export interface NotificationFilters {
  type?: NotificationType;
  category?: NotificationCategory;
  read?: boolean;
}

export interface NotificationState {
  /** List of all notifications */
  notifications: Notification[];
  /** Maximum number of notifications to keep */
  maxNotifications: number;
  /** Whether to show toast notifications */
  showToasts: boolean;
  /** Toast duration in milliseconds */
  toastDuration: number;
}

export interface NotificationActions {
  /** Add a new notification */
  addNotification: (input: NotificationInput) => Notification;
  /** Mark a notification as read */
  markAsRead: (notificationId: string) => void;
  /** Mark all notifications as read */
  markAllAsRead: () => void;
  /** Remove a notification */
  removeNotification: (notificationId: string) => void;
  /** Clear all notifications */
  clearAll: () => void;
  /** Clear read notifications */
  clearRead: () => void;
  /** Get filtered notifications */
  getFiltered: (filters: NotificationFilters) => Notification[];
  /** Get unread count */
  getUnreadCount: () => number;
  /** Get unread count by category */
  getUnreadCountByCategory: (category: NotificationCategory) => number;
  /** Update settings */
  updateSettings: (settings: Partial<Pick<NotificationState, 'maxNotifications' | 'showToasts' | 'toastDuration'>>) => void;
}

export type NotificationStore = NotificationState & NotificationActions;

// ============================================================================
// Utilities
// ============================================================================

function generateNotificationId(): string {
  return `notif_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// ============================================================================
// Store Implementation
// ============================================================================

export const useNotificationStore = create<NotificationStore>()(
  devtools(
    persist(
      (set, get) => ({
        // ============================================================================
        // State
        // ============================================================================
        notifications: [],
        maxNotifications: 100,
        showToasts: true,
        toastDuration: 5000,

        // ============================================================================
        // Actions
        // ============================================================================

        addNotification: (input: NotificationInput): Notification => {
          const notification: Notification = {
            id: generateNotificationId(),
            type: input.type,
            category: input.category,
            title: input.title,
            message: input.message,
            data: input.data,
            link: input.link,
            read: false,
            createdAt: new Date().toISOString(),
          };

          set((state) => {
            // Add new notification at the beginning
            const updated = [notification, ...state.notifications];

            // Trim to max notifications
            const trimmed = updated.slice(0, state.maxNotifications);

            return { notifications: trimmed };
          });

          return notification;
        },

        markAsRead: (notificationId: string): void => {
          set((state) => ({
            notifications: state.notifications.map((n) =>
              n.id === notificationId ? { ...n, read: true } : n
            ),
          }));
        },

        markAllAsRead: (): void => {
          set((state) => ({
            notifications: state.notifications.map((n) => ({
              ...n,
              read: true,
            })),
          }));
        },

        removeNotification: (notificationId: string): void => {
          set((state) => ({
            notifications: state.notifications.filter(
              (n) => n.id !== notificationId
            ),
          }));
        },

        clearAll: (): void => {
          set({ notifications: [] });
        },

        clearRead: (): void => {
          set((state) => ({
            notifications: state.notifications.filter((n) => !n.read),
          }));
        },

        getFiltered: (filters: NotificationFilters): Notification[] => {
          const { notifications } = get();

          return notifications.filter((n) => {
            if (filters.type !== undefined && n.type !== filters.type) {
              return false;
            }
            if (filters.category !== undefined && n.category !== filters.category) {
              return false;
            }
            if (filters.read !== undefined && n.read !== filters.read) {
              return false;
            }
            return true;
          });
        },

        getUnreadCount: (): number => {
          return get().notifications.filter((n) => !n.read).length;
        },

        getUnreadCountByCategory: (category: NotificationCategory): number => {
          return get().notifications.filter(
            (n) => !n.read && n.category === category
          ).length;
        },

        updateSettings: (
          settings: Partial<
            Pick<NotificationState, 'maxNotifications' | 'showToasts' | 'toastDuration'>
          >
        ): void => {
          set(settings);
        },
      }),
      {
        name: 'garageswarm-notifications',
        // Only persist notifications and settings, not computed values
        partialize: (state) => ({
          notifications: state.notifications,
          maxNotifications: state.maxNotifications,
          showToasts: state.showToasts,
          toastDuration: state.toastDuration,
        }),
      }
    ),
    { name: 'NotificationStore' }
  )
);

// ============================================================================
// Selectors
// ============================================================================

/**
 * Select all notifications
 */
export const selectNotifications = (state: NotificationStore): Notification[] =>
  state.notifications;

/**
 * Select unread notifications
 */
export const selectUnreadNotifications = (
  state: NotificationStore
): Notification[] => state.notifications.filter((n) => !n.read);

/**
 * Select unread count
 */
export const selectUnreadCount = (state: NotificationStore): number =>
  state.notifications.filter((n) => !n.read).length;

/**
 * Select notifications by category
 */
export const selectNotificationsByCategory = (
  category: NotificationCategory
) => (state: NotificationStore): Notification[] =>
  state.notifications.filter((n) => n.category === category);

/**
 * Select recent notifications (last N)
 */
export const selectRecentNotifications = (limit: number) => (
  state: NotificationStore
): Notification[] => state.notifications.slice(0, limit);

/**
 * Select if there are any unread notifications
 */
export const selectHasUnread = (state: NotificationStore): boolean =>
  state.notifications.some((n) => !n.read);

/**
 * Select toast settings
 */
export const selectToastSettings = (
  state: NotificationStore
): { showToasts: boolean; toastDuration: number } => ({
  showToasts: state.showToasts,
  toastDuration: state.toastDuration,
});

// ============================================================================
// Hook Helpers
// ============================================================================

/**
 * Get typed notification actions (for use outside React components)
 */
export const notificationActions = {
  add: (input: NotificationInput): Notification =>
    useNotificationStore.getState().addNotification(input),
  markAsRead: (id: string): void =>
    useNotificationStore.getState().markAsRead(id),
  markAllAsRead: (): void =>
    useNotificationStore.getState().markAllAsRead(),
  remove: (id: string): void =>
    useNotificationStore.getState().removeNotification(id),
  clearAll: (): void =>
    useNotificationStore.getState().clearAll(),
  clearRead: (): void =>
    useNotificationStore.getState().clearRead(),
};

export default useNotificationStore;
