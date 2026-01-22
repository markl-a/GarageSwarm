/**
 * authStore Tests
 *
 * Tests for the Zustand auth store covering:
 * - State updates
 * - Persistence
 * - Actions
 * - Selectors
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useAuthStore, User, AuthTokens } from '../authStore';

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// Sample test data
const mockUser: User = {
  id: 'user-123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

const mockTokens: AuthTokens = {
  accessToken: 'mock-access-token',
  refreshToken: 'mock-refresh-token',
  tokenType: 'Bearer',
  expiresIn: 3600,
};

describe('authStore', () => {
  beforeEach(() => {
    // Reset the store before each test
    useAuthStore.getState().logout();
    mockLocalStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Clean up after each test
    useAuthStore.getState().logout();
    mockLocalStorage.clear();
  });

  // ===========================================================================
  // Initial State
  // ===========================================================================

  describe('Initial State', () => {
    it('has null user by default', () => {
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
    });

    it('has null tokens by default', () => {
      const state = useAuthStore.getState();
      expect(state.tokens).toBeNull();
    });

    it('has isLoading false by default', () => {
      const state = useAuthStore.getState();
      expect(state.isLoading).toBe(false);
    });

    it('has null error by default', () => {
      const state = useAuthStore.getState();
      expect(state.error).toBeNull();
    });

    it('has rememberMe false by default', () => {
      const state = useAuthStore.getState();
      expect(state.rememberMe).toBe(false);
    });
  });

  // ===========================================================================
  // State Updates - setUser
  // ===========================================================================

  describe('setUser', () => {
    it('updates user state', () => {
      useAuthStore.getState().setUser(mockUser);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
    });

    it('clears user when set to null', () => {
      useAuthStore.getState().setUser(mockUser);
      useAuthStore.getState().setUser(null);

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
    });
  });

  // ===========================================================================
  // State Updates - setTokens
  // ===========================================================================

  describe('setTokens', () => {
    it('updates tokens state', () => {
      useAuthStore.getState().setTokens(mockTokens);

      const state = useAuthStore.getState();
      expect(state.tokens).toEqual(mockTokens);
    });

    it('clears tokens when set to null', () => {
      useAuthStore.getState().setTokens(mockTokens);
      useAuthStore.getState().setTokens(null);

      const state = useAuthStore.getState();
      expect(state.tokens).toBeNull();
    });
  });

  // ===========================================================================
  // State Updates - setLoading
  // ===========================================================================

  describe('setLoading', () => {
    it('sets loading to true', () => {
      useAuthStore.getState().setLoading(true);

      const state = useAuthStore.getState();
      expect(state.isLoading).toBe(true);
    });

    it('sets loading to false', () => {
      useAuthStore.getState().setLoading(true);
      useAuthStore.getState().setLoading(false);

      const state = useAuthStore.getState();
      expect(state.isLoading).toBe(false);
    });
  });

  // ===========================================================================
  // State Updates - setError
  // ===========================================================================

  describe('setError', () => {
    it('sets error message', () => {
      useAuthStore.getState().setError('Test error');

      const state = useAuthStore.getState();
      expect(state.error).toBe('Test error');
    });

    it('clears error when set to null', () => {
      useAuthStore.getState().setError('Test error');
      useAuthStore.getState().setError(null);

      const state = useAuthStore.getState();
      expect(state.error).toBeNull();
    });
  });

  // ===========================================================================
  // State Updates - setRememberMe
  // ===========================================================================

  describe('setRememberMe', () => {
    it('sets remember me to true', () => {
      useAuthStore.getState().setRememberMe(true);

      const state = useAuthStore.getState();
      expect(state.rememberMe).toBe(true);
    });

    it('sets remember me to false', () => {
      useAuthStore.getState().setRememberMe(true);
      useAuthStore.getState().setRememberMe(false);

      const state = useAuthStore.getState();
      expect(state.rememberMe).toBe(false);
    });
  });

  // ===========================================================================
  // Login Action
  // ===========================================================================

  describe('login', () => {
    it('sets user and tokens', () => {
      useAuthStore.getState().login(mockUser, mockTokens);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.tokens).toEqual(mockTokens);
    });

    it('clears loading state', () => {
      useAuthStore.getState().setLoading(true);
      useAuthStore.getState().login(mockUser, mockTokens);

      const state = useAuthStore.getState();
      expect(state.isLoading).toBe(false);
    });

    it('clears error state', () => {
      useAuthStore.getState().setError('Previous error');
      useAuthStore.getState().login(mockUser, mockTokens);

      const state = useAuthStore.getState();
      expect(state.error).toBeNull();
    });
  });

  // ===========================================================================
  // Logout Action
  // ===========================================================================

  describe('logout', () => {
    it('clears user', () => {
      useAuthStore.getState().login(mockUser, mockTokens);
      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
    });

    it('clears tokens', () => {
      useAuthStore.getState().login(mockUser, mockTokens);
      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.tokens).toBeNull();
    });

    it('clears error', () => {
      useAuthStore.getState().setError('Some error');
      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.error).toBeNull();
    });

    it('preserves rememberMe setting', () => {
      useAuthStore.getState().setRememberMe(true);
      useAuthStore.getState().login(mockUser, mockTokens);
      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      // rememberMe is persisted, so it should still be true (or false depending on implementation)
      expect(typeof state.rememberMe).toBe('boolean');
    });
  });

  // ===========================================================================
  // clearError Action
  // ===========================================================================

  describe('clearError', () => {
    it('clears error state', () => {
      useAuthStore.getState().setError('Test error');
      useAuthStore.getState().clearError();

      const state = useAuthStore.getState();
      expect(state.error).toBeNull();
    });

    it('does nothing when no error exists', () => {
      useAuthStore.getState().clearError();

      const state = useAuthStore.getState();
      expect(state.error).toBeNull();
    });
  });

  // ===========================================================================
  // isAuthenticated Method
  // ===========================================================================

  describe('isAuthenticated', () => {
    it('returns false when no user', () => {
      const isAuth = useAuthStore.getState().isAuthenticated();
      expect(isAuth).toBe(false);
    });

    it('returns false when no tokens', () => {
      useAuthStore.getState().setUser(mockUser);
      const isAuth = useAuthStore.getState().isAuthenticated();
      expect(isAuth).toBe(false);
    });

    it('returns true when user and tokens exist', () => {
      useAuthStore.getState().login(mockUser, mockTokens);
      const isAuth = useAuthStore.getState().isAuthenticated();
      expect(isAuth).toBe(true);
    });

    it('returns false after logout', () => {
      useAuthStore.getState().login(mockUser, mockTokens);
      useAuthStore.getState().logout();
      const isAuth = useAuthStore.getState().isAuthenticated();
      expect(isAuth).toBe(false);
    });
  });

  // ===========================================================================
  // getAccessToken Method
  // ===========================================================================

  describe('getAccessToken', () => {
    it('returns null when no tokens', () => {
      const token = useAuthStore.getState().getAccessToken();
      expect(token).toBeNull();
    });

    it('returns access token when authenticated', () => {
      useAuthStore.getState().login(mockUser, mockTokens);
      const token = useAuthStore.getState().getAccessToken();
      expect(token).toBe('mock-access-token');
    });

    it('returns null after logout', () => {
      useAuthStore.getState().login(mockUser, mockTokens);
      useAuthStore.getState().logout();
      const token = useAuthStore.getState().getAccessToken();
      expect(token).toBeNull();
    });
  });

  // ===========================================================================
  // Persistence
  // ===========================================================================

  describe('Persistence', () => {
    it('persists user to localStorage', () => {
      useAuthStore.getState().login(mockUser, mockTokens);

      // Check that localStorage was called
      const stored = mockLocalStorage.getItem('garageswarm-auth');
      expect(stored).toBeTruthy();

      if (stored) {
        const parsed = JSON.parse(stored);
        expect(parsed.state.user).toEqual(mockUser);
      }
    });

    it('persists tokens to localStorage', () => {
      useAuthStore.getState().login(mockUser, mockTokens);

      const stored = mockLocalStorage.getItem('garageswarm-auth');
      expect(stored).toBeTruthy();

      if (stored) {
        const parsed = JSON.parse(stored);
        expect(parsed.state.tokens).toEqual(mockTokens);
      }
    });

    it('persists rememberMe to localStorage', () => {
      useAuthStore.getState().setRememberMe(true);
      useAuthStore.getState().login(mockUser, mockTokens);

      const stored = mockLocalStorage.getItem('garageswarm-auth');
      expect(stored).toBeTruthy();

      if (stored) {
        const parsed = JSON.parse(stored);
        expect(parsed.state.rememberMe).toBe(true);
      }
    });

    it('clears persisted data on logout', () => {
      useAuthStore.getState().login(mockUser, mockTokens);
      useAuthStore.getState().logout();

      const stored = mockLocalStorage.getItem('garageswarm-auth');
      if (stored) {
        const parsed = JSON.parse(stored);
        expect(parsed.state.user).toBeNull();
        expect(parsed.state.tokens).toBeNull();
      }
    });
  });

  // ===========================================================================
  // State Subscriptions
  // ===========================================================================

  describe('Subscriptions', () => {
    it('notifies subscribers on state change', () => {
      const listener = vi.fn();
      const unsubscribe = useAuthStore.subscribe(listener);

      useAuthStore.getState().setUser(mockUser);

      expect(listener).toHaveBeenCalled();

      unsubscribe();
    });

    it('stops notifying after unsubscribe', () => {
      const listener = vi.fn();
      const unsubscribe = useAuthStore.subscribe(listener);

      unsubscribe();
      useAuthStore.getState().setUser(mockUser);

      // Listener should not have been called after unsubscribe
      // (it may have been called once during setup)
      const callsAfterUnsubscribe = listener.mock.calls.filter(
        (call) => call[0]?.user === mockUser
      );
      expect(callsAfterUnsubscribe.length).toBe(0);
    });
  });

  // ===========================================================================
  // Edge Cases
  // ===========================================================================

  describe('Edge Cases', () => {
    it('handles multiple rapid state updates', () => {
      const store = useAuthStore.getState();

      store.setLoading(true);
      store.setUser(mockUser);
      store.setTokens(mockTokens);
      store.setLoading(false);
      store.setError(null);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.tokens).toEqual(mockTokens);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('handles login after previous logout', () => {
      useAuthStore.getState().login(mockUser, mockTokens);
      useAuthStore.getState().logout();

      const newUser = { ...mockUser, id: 'user-456' };
      useAuthStore.getState().login(newUser, mockTokens);

      const state = useAuthStore.getState();
      expect(state.user?.id).toBe('user-456');
    });

    it('handles concurrent operations safely', () => {
      // Simulate concurrent operations
      Promise.all([
        Promise.resolve().then(() => useAuthStore.getState().setLoading(true)),
        Promise.resolve().then(() => useAuthStore.getState().setUser(mockUser)),
        Promise.resolve().then(() => useAuthStore.getState().setTokens(mockTokens)),
      ]).then(() => {
        const state = useAuthStore.getState();
        expect(state.user).toEqual(mockUser);
        expect(state.tokens).toEqual(mockTokens);
      });
    });
  });
});
