/**
 * useAuth Hook Tests
 *
 * Tests for the useAuth hook covering:
 * - Login flow
 * - Token storage
 * - Logout
 * - Error handling
 * - User state management
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { useAuth } from '../useAuth';
import { useAuthStore } from '@/stores/authStore';
import { server } from '@/test/mocks/server';
import { mockUser, mockTokens } from '@/test/mocks/api';
import { http, HttpResponse } from 'msw';

// Create a wrapper component with all required providers
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('useAuth Hook', () => {
  beforeEach(() => {
    // Reset the auth store before each test
    useAuthStore.getState().logout();
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Clean up after each test
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  // ===========================================================================
  // Initial State
  // ===========================================================================

  describe('Initial State', () => {
    it('returns initial unauthenticated state', () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('returns login and logout functions', () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.login).toBe('function');
      expect(typeof result.current.logout).toBe('function');
    });

    it('returns error clearing function', () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.clearError).toBe('function');
    });
  });

  // ===========================================================================
  // Login Flow
  // ===========================================================================

  describe('Login Flow', () => {
    it('logs in successfully with valid credentials', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      // Wait for the login mutation to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // After successful login, check store state
      const storeState = useAuthStore.getState();
      expect(storeState.user).toBeDefined();
      expect(storeState.tokens).toBeDefined();
    });

    it('sets loading state during login', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      let wasLoading = false;

      act(() => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
        wasLoading = result.current.isLoading;
      });

      // Check that loading was true at some point
      expect(wasLoading || result.current.isLoading).toBe(true);
    });

    it('handles login error with invalid credentials', async () => {
      server.use(
        http.post('http://127.0.0.1:8000/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Invalid credentials' },
            { status: 401 }
          );
        })
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.login({
          email: 'wrong@example.com',
          password: 'wrongpassword',
        });
      });

      // Wait for the mutation to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Check that error is set
      const storeState = useAuthStore.getState();
      expect(storeState.error).toBeTruthy();
    });

    it('clears previous error before new login attempt', async () => {
      // First, set an error in the store
      useAuthStore.getState().setError('Previous error');

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      // Error should be cleared before login attempt
      await waitFor(() => {
        expect(result.current.error).toBeNull();
      });
    });
  });

  // ===========================================================================
  // Token Storage
  // ===========================================================================

  describe('Token Storage', () => {
    it('stores tokens after successful login', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Check that tokens are stored in the auth store
      const storeState = useAuthStore.getState();
      expect(storeState.tokens?.accessToken).toBeDefined();
      expect(storeState.tokens?.refreshToken).toBeDefined();
    });

    it('retrieves stored user on subsequent renders', async () => {
      // First, log in
      const { result: loginResult } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        loginResult.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      await waitFor(() => {
        expect(loginResult.current.isLoading).toBe(false);
      });

      // Create a new render of the hook
      const { result: newResult } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      // Should have the user from the store
      expect(newResult.current.user).toBeDefined();
    });
  });

  // ===========================================================================
  // Logout
  // ===========================================================================

  describe('Logout', () => {
    it('clears user state on logout', async () => {
      // First, log in
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      await waitFor(() => {
        const storeState = useAuthStore.getState();
        expect(storeState.user).toBeDefined();
      });

      // Now logout
      await act(async () => {
        await result.current.logout();
      });

      // Check that state is cleared
      const storeState = useAuthStore.getState();
      expect(storeState.user).toBeNull();
      expect(storeState.tokens).toBeNull();
    });

    it('clears tokens on logout', async () => {
      // First, log in
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      await waitFor(() => {
        const storeState = useAuthStore.getState();
        expect(storeState.tokens).toBeDefined();
      });

      // Now logout
      await act(async () => {
        await result.current.logout();
      });

      // Check that tokens are cleared
      const storeState = useAuthStore.getState();
      expect(storeState.tokens).toBeNull();
    });

    it('handles logout even if API call fails', async () => {
      // Mock logout API to fail
      server.use(
        http.post('http://127.0.0.1:8000/api/v1/auth/logout', () => {
          return HttpResponse.json(
            { detail: 'Server error' },
            { status: 500 }
          );
        })
      );

      // First, set up authenticated state
      useAuthStore.getState().login(
        {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
        {
          accessToken: 'test-access-token',
          refreshToken: 'test-refresh-token',
          tokenType: 'Bearer',
          expiresIn: 3600,
        }
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      // Logout should still work even if API fails
      await act(async () => {
        await result.current.logout();
      });

      // User should be logged out locally
      const storeState = useAuthStore.getState();
      expect(storeState.user).toBeNull();
      expect(storeState.tokens).toBeNull();
    });
  });

  // ===========================================================================
  // Error Handling
  // ===========================================================================

  describe('Error Handling', () => {
    it('sets error on network failure', async () => {
      server.use(
        http.post('http://127.0.0.1:8000/api/v1/auth/login', () => {
          return HttpResponse.error();
        })
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should have an error
      const storeState = useAuthStore.getState();
      expect(storeState.error).toBeTruthy();
    });

    it('clears error with clearError function', async () => {
      // Set an error
      useAuthStore.getState().setError('Test error');

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      expect(result.current.error).toBe('Test error');

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });

  // ===========================================================================
  // Authentication Check
  // ===========================================================================

  describe('Authentication Check', () => {
    it('returns false when not authenticated', () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isAuthenticated).toBe(false);
    });

    it('returns true when authenticated', () => {
      // Set up authenticated state
      useAuthStore.getState().login(
        {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
        {
          accessToken: 'test-access-token',
          refreshToken: 'test-refresh-token',
          tokenType: 'Bearer',
          expiresIn: 3600,
        }
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isAuthenticated).toBe(true);
    });
  });

  // ===========================================================================
  // Remember Me
  // ===========================================================================

  describe('Remember Me', () => {
    it('stores remember me preference', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setRememberMe(true);
      });

      const storeState = useAuthStore.getState();
      expect(storeState.rememberMe).toBe(true);
    });

    it('passes remember me to login', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123',
          rememberMe: true,
        });
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const storeState = useAuthStore.getState();
      expect(storeState.rememberMe).toBe(true);
    });
  });
});
