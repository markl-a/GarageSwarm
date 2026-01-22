import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useLocation } from 'react-router-dom';
import { useCallback, useEffect } from 'react';
import { useAuthStore, User, AuthTokens } from '@/stores/authStore';
import axios, { AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// API client with auth interceptor
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && originalRequest && !originalRequest.headers['X-Retry']) {
      const tokens = useAuthStore.getState().tokens;
      if (tokens?.refreshToken) {
        try {
          const response = await axios.post<AuthTokens>(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refreshToken: tokens.refreshToken,
          });
          useAuthStore.getState().setTokens(response.data);
          originalRequest.headers['Authorization'] = `Bearer ${response.data.accessToken}`;
          originalRequest.headers['X-Retry'] = 'true';
          return apiClient(originalRequest);
        } catch {
          useAuthStore.getState().logout();
        }
      }
    }
    return Promise.reject(error);
  }
);

// Types
interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

interface RegisterData {
  name: string;
  email: string;
  password: string;
}

interface ForgotPasswordData {
  email: string;
}

interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

interface ApiError {
  detail: string;
  status_code?: number;
}

// API functions
const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/v1/auth/login', {
      email: credentials.email,
      password: credentials.password,
    });
    return response.data;
  },

  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/v1/auth/register', data);
    return response.data;
  },

  forgotPassword: async (data: ForgotPasswordData): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/api/v1/auth/forgot-password', data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/api/v1/auth/logout');
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/v1/auth/me');
    return response.data;
  },

  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    const response = await apiClient.post<AuthTokens>('/api/v1/auth/refresh', {
      refreshToken,
    });
    return response.data;
  },
};

// Hook
export function useAuth() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  const {
    user,
    tokens,
    isLoading,
    error,
    rememberMe,
    login: storeLogin,
    logout: storeLogout,
    setLoading,
    setError,
    setRememberMe,
    clearError,
    isAuthenticated,
  } = useAuthStore();

  // Current user query
  const userQuery = useQuery({
    queryKey: ['currentUser'],
    queryFn: authApi.getCurrentUser,
    enabled: !!tokens?.accessToken,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Update store when user query succeeds
  useEffect(() => {
    if (userQuery.data) {
      useAuthStore.getState().setUser(userQuery.data);
    }
  }, [userQuery.data]);

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onMutate: () => {
      setLoading(true);
      clearError();
    },
    onSuccess: (data, variables) => {
      storeLogin(data.user, data.tokens);
      setRememberMe(variables.rememberMe ?? false);
      queryClient.setQueryData(['currentUser'], data.user);

      // Redirect to intended page or dashboard
      const from = (location.state as { from?: Location })?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    },
    onError: (error: AxiosError<ApiError>) => {
      setLoading(false);
      const message = error.response?.data?.detail || 'Login failed. Please try again.';
      setError(message);
    },
  });

  // Register mutation
  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onMutate: () => {
      setLoading(true);
      clearError();
    },
    onSuccess: () => {
      setLoading(false);
      navigate('/login', {
        state: { message: 'Registration successful! Please log in.' },
        replace: true,
      });
    },
    onError: (error: AxiosError<ApiError>) => {
      setLoading(false);
      const message = error.response?.data?.detail || 'Registration failed. Please try again.';
      setError(message);
    },
  });

  // Forgot password mutation
  const forgotPasswordMutation = useMutation({
    mutationFn: authApi.forgotPassword,
    onMutate: () => {
      setLoading(true);
      clearError();
    },
    onSuccess: () => {
      setLoading(false);
    },
    onError: (error: AxiosError<ApiError>) => {
      setLoading(false);
      const message = error.response?.data?.detail || 'Failed to send reset email. Please try again.';
      setError(message);
    },
  });

  // Logout function
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore logout API errors
    } finally {
      storeLogout();
      queryClient.clear();
      navigate('/login', { replace: true });
    }
  }, [storeLogout, queryClient, navigate]);

  // Check if user is authenticated
  const checkAuth = useCallback((): boolean => {
    return isAuthenticated();
  }, [isAuthenticated]);

  return {
    // State
    user,
    tokens,
    isLoading: isLoading || loginMutation.isPending || registerMutation.isPending || forgotPasswordMutation.isPending,
    error,
    rememberMe,
    isAuthenticated: checkAuth(),

    // Actions
    login: loginMutation.mutate,
    register: registerMutation.mutate,
    forgotPassword: forgotPasswordMutation.mutate,
    logout,
    clearError,
    setRememberMe,

    // Mutation states
    loginMutation,
    registerMutation,
    forgotPasswordMutation,
    userQuery,
  };
}

// Hook for protected routes
export function useRequireAuth(redirectTo: string = '/login') {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isLoading, userQuery } = useAuth();

  useEffect(() => {
    if (!isLoading && !userQuery.isLoading && !isAuthenticated) {
      navigate(redirectTo, {
        replace: true,
        state: { from: location }
      });
    }
  }, [isAuthenticated, isLoading, userQuery.isLoading, navigate, location, redirectTo]);

  return {
    isAuthenticated,
    isLoading: isLoading || userQuery.isLoading,
  };
}

export { apiClient };
