/**
 * NotificationCenter Component
 *
 * A comprehensive notification center with bell icon, badge,
 * dropdown list, and toast notifications.
 */

import React, { useCallback, useEffect, useRef } from 'react';
import { useNotifications, ToastNotification } from '../../hooks/useNotifications';
import {
  Notification,
  NotificationType,
  NotificationCategory,
} from '../../types/websocket';

// ============================================================================
// Utility Functions
// ============================================================================

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return date.toLocaleDateString();
}

function getNotificationTypeStyles(type: NotificationType): {
  bgColor: string;
  textColor: string;
  borderColor: string;
  iconBgColor: string;
} {
  switch (type) {
    case NotificationType.SUCCESS:
      return {
        bgColor: 'bg-green-50',
        textColor: 'text-green-800',
        borderColor: 'border-green-200',
        iconBgColor: 'bg-green-100',
      };
    case NotificationType.ERROR:
      return {
        bgColor: 'bg-red-50',
        textColor: 'text-red-800',
        borderColor: 'border-red-200',
        iconBgColor: 'bg-red-100',
      };
    case NotificationType.WARNING:
      return {
        bgColor: 'bg-yellow-50',
        textColor: 'text-yellow-800',
        borderColor: 'border-yellow-200',
        iconBgColor: 'bg-yellow-100',
      };
    case NotificationType.INFO:
    default:
      return {
        bgColor: 'bg-blue-50',
        textColor: 'text-blue-800',
        borderColor: 'border-blue-200',
        iconBgColor: 'bg-blue-100',
      };
  }
}

function getCategoryIcon(category: NotificationCategory): React.ReactNode {
  switch (category) {
    case NotificationCategory.TASK:
      return (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
          />
        </svg>
      );
    case NotificationCategory.WORKER:
      return (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
          />
        </svg>
      );
    case NotificationCategory.WORKFLOW:
      return (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
          />
        </svg>
      );
    case NotificationCategory.SYSTEM:
    default:
      return (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      );
  }
}

function getTypeIcon(type: NotificationType): React.ReactNode {
  switch (type) {
    case NotificationType.SUCCESS:
      return (
        <svg
          className="w-5 h-5 text-green-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      );
    case NotificationType.ERROR:
      return (
        <svg
          className="w-5 h-5 text-red-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      );
    case NotificationType.WARNING:
      return (
        <svg
          className="w-5 h-5 text-yellow-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      );
    case NotificationType.INFO:
    default:
      return (
        <svg
          className="w-5 h-5 text-blue-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      );
  }
}

// ============================================================================
// NotificationItem Component
// ============================================================================

interface NotificationItemProps {
  notification: Notification;
  onClick?: () => void;
  onDismiss?: () => void;
  compact?: boolean;
}

const NotificationItem: React.FC<NotificationItemProps> = ({
  notification,
  onClick,
  onDismiss,
  compact = false,
}) => {
  const styles = getNotificationTypeStyles(notification.type);

  return (
    <div
      className={`
        ${styles.bgColor} ${styles.borderColor}
        border rounded-lg p-3 cursor-pointer
        hover:shadow-sm transition-shadow duration-200
        ${notification.read ? 'opacity-60' : ''}
        ${compact ? 'py-2' : ''}
      `}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        {/* Type Icon */}
        <div className={`${styles.iconBgColor} rounded-full p-1.5 flex-shrink-0`}>
          {getTypeIcon(notification.type)}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className={`font-medium ${styles.textColor} truncate`}>
              {notification.title}
            </h4>
            {!notification.read && (
              <span className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" />
            )}
          </div>
          {!compact && (
            <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">
              {notification.message}
            </p>
          )}
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-gray-400 flex items-center gap-1">
              {getCategoryIcon(notification.category)}
              {notification.category}
            </span>
            <span className="text-xs text-gray-400">
              {formatTimeAgo(notification.createdAt)}
            </span>
          </div>
        </div>

        {/* Dismiss Button */}
        {onDismiss && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDismiss();
            }}
            className="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-100 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Toast Component
// ============================================================================

interface ToastProps {
  toast: ToastNotification;
  onDismiss: () => void;
  onClick?: () => void;
}

const Toast: React.FC<ToastProps> = ({ toast, onDismiss, onClick }) => {
  const { notification, exiting } = toast;
  const styles = getNotificationTypeStyles(notification.type);

  return (
    <div
      className={`
        ${styles.bgColor} ${styles.borderColor}
        border rounded-lg shadow-lg p-4 max-w-sm w-full
        transform transition-all duration-300 ease-in-out
        ${exiting ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100'}
        cursor-pointer hover:shadow-xl
      `}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className={`${styles.iconBgColor} rounded-full p-1.5 flex-shrink-0`}>
          {getTypeIcon(notification.type)}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className={`font-medium ${styles.textColor}`}>
            {notification.title}
          </h4>
          <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">
            {notification.message}
          </p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDismiss();
          }}
          className="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-100 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// ToastContainer Component
// ============================================================================

interface ToastContainerProps {
  toasts: ToastNotification[];
  onDismiss: (toastId: string) => void;
  onToastClick?: (notification: Notification) => void;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

export const ToastContainer: React.FC<ToastContainerProps> = ({
  toasts,
  onDismiss,
  onToastClick,
  position = 'top-right',
}) => {
  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
  };

  return (
    <div
      className={`fixed ${positionClasses[position]} z-50 flex flex-col gap-2`}
    >
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          toast={toast}
          onDismiss={() => onDismiss(toast.id)}
          onClick={
            onToastClick
              ? () => onToastClick(toast.notification)
              : undefined
          }
        />
      ))}
    </div>
  );
};

// ============================================================================
// NotificationCenter Component
// ============================================================================

export interface NotificationCenterProps {
  /** Maximum notifications to show in the dropdown */
  maxVisible?: number;
  /** Position of toast notifications */
  toastPosition?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  /** Custom class for the container */
  className?: string;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  maxVisible = 10,
  toastPosition = 'top-right',
  className = '',
}) => {
  const dropdownRef = useRef<HTMLDivElement>(null);

  const {
    notifications,
    unreadCount,
    toasts,
    isOpen,
    open,
    close,
    toggle,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    dismissToast,
    navigateToNotification,
  } = useNotifications();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        close();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, close]);

  // Close dropdown on escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, close]);

  const handleNotificationClick = useCallback(
    (notification: Notification) => {
      navigateToNotification(notification);
    },
    [navigateToNotification]
  );

  const visibleNotifications = notifications.slice(0, maxVisible);
  const hasMore = notifications.length > maxVisible;

  return (
    <>
      {/* Toast Container */}
      <ToastContainer
        toasts={toasts}
        onDismiss={dismissToast}
        onToastClick={handleNotificationClick}
        position={toastPosition}
      />

      {/* Notification Bell and Dropdown */}
      <div ref={dropdownRef} className={`relative ${className}`}>
        {/* Bell Button */}
        <button
          onClick={toggle}
          className="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-full transition-colors"
          aria-label="Notifications"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
            />
          </svg>

          {/* Badge */}
          {unreadCount > 0 && (
            <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-500 rounded-full min-w-[20px]">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </button>

        {/* Dropdown */}
        {isOpen && (
          <div className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
              <h3 className="font-semibold text-gray-900">Notifications</h3>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Mark all read
                  </button>
                )}
                {notifications.length > 0 && (
                  <button
                    onClick={clearAll}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    Clear all
                  </button>
                )}
              </div>
            </div>

            {/* Notification List */}
            <div className="max-h-96 overflow-y-auto">
              {visibleNotifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                  <svg
                    className="w-12 h-12 mb-3 text-gray-300"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                    />
                  </svg>
                  <p className="text-sm">No notifications yet</p>
                </div>
              ) : (
                <div className="p-2 space-y-2">
                  {visibleNotifications.map((notification) => (
                    <NotificationItem
                      key={notification.id}
                      notification={notification}
                      onClick={() => handleNotificationClick(notification)}
                      onDismiss={() => removeNotification(notification.id)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            {hasMore && (
              <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 text-center">
                <button
                  onClick={() => {
                    close();
                    // Navigate to notifications page
                    // navigate('/notifications');
                  }}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  View all {notifications.length} notifications
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
};

// ============================================================================
// Exports
// ============================================================================

export { NotificationItem, Toast };
export default NotificationCenter;
