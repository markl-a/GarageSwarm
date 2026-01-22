/**
 * Base API Client Service
 *
 * Configures axios instance with:
 * - Base URL from environment
 * - Request/Response interceptors
 * - JWT token handling
 * - Automatic token refresh
 * - Error handling
 */

import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios';
import type { TokenResponse, ApiError } from '../types/api';

// =============================================================================
// Configuration
// =============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const API_VERSION = '/api/v1';

// Token storage keys
const ACCESS_TOKEN_KEY = 'garageswarm_access_token';
const REFRESH_TOKEN_KEY = 'garageswarm_refresh_token';
const TOKEN_EXPIRY_KEY = 'garageswarm_token_expiry';

// =============================================================================
// Token Management
// =============================================================================

export interface TokenStorage {
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  setTokens: (tokens: TokenResponse) => void;
  clearTokens: () => void;
  isTokenExpired: () => boolean;
}

/**
 * Default token storage implementation using localStorage
 */
export const tokenStorage: TokenStorage = {
  getAccessToken: (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  getRefreshToken: (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setTokens: (tokens: TokenResponse): void => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    // Store expiry timestamp (current time + expires_in seconds)
    const expiryTime = Date.now() + tokens.expires_in * 1000;
    localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());
  },

  clearTokens: (): void => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
  },

  isTokenExpired: (): boolean => {
    if (typeof window === 'undefined') return true;
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);
    if (!expiry) return true;
    // Consider token expired if less than 30 seconds remaining
    return Date.now() >= parseInt(expiry, 10) - 30000;
  },
};

// =============================================================================
// API Client Creation
// =============================================================================

/**
 * Creates the base axios instance with interceptors
 */
function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: `${API_BASE_URL}${API_VERSION}`,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Track if we're currently refreshing to prevent infinite loops
  let isRefreshing = false;
  let failedQueue: Array<{
    resolve: (value: unknown) => void;
    reject: (reason: unknown) => void;
  }> = [];

  const processQueue = (error: Error | null, token: string | null = null): void => {
    failedQueue.forEach((promise) => {
      if (error) {
        promise.reject(error);
      } else {
        promise.resolve(token);
      }
    });
    failedQueue = [];
  };

  // Request interceptor - Add auth token to requests
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
      const token = tokenStorage.getAccessToken();
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error: AxiosError): Promise<never> => {
      return Promise.reject(error);
    }
  );

  // Response interceptor - Handle errors and token refresh
  client.interceptors.response.use(
    (response: AxiosResponse): AxiosResponse => {
      return response;
    },
    async (error: AxiosError<ApiError>): Promise<AxiosResponse> => {
      const originalRequest = error.config as InternalAxiosRequestConfig & {
        _retry?: boolean;
      };

      // If error is 401 and we haven't already tried to refresh
      if (error.response?.status === 401 && !originalRequest._retry) {
        // Don't try to refresh if this is already a refresh or login request
        if (
          originalRequest.url?.includes('/auth/refresh') ||
          originalRequest.url?.includes('/auth/login')
        ) {
          return Promise.reject(error);
        }

        if (isRefreshing) {
          // If already refreshing, queue this request
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((token) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              return client(originalRequest);
            })
            .catch((err) => {
              return Promise.reject(err);
            });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        const refreshToken = tokenStorage.getRefreshToken();
        if (!refreshToken) {
          isRefreshing = false;
          tokenStorage.clearTokens();
          // Emit event for auth state change
          window.dispatchEvent(new CustomEvent('auth:logout'));
          return Promise.reject(error);
        }

        try {
          const response = await axios.post<TokenResponse>(
            `${API_BASE_URL}${API_VERSION}/auth/refresh`,
            { refresh_token: refreshToken },
            { headers: { 'Content-Type': 'application/json' } }
          );

          const tokens = response.data;
          tokenStorage.setTokens(tokens);

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
          }

          processQueue(null, tokens.access_token);

          return client(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError as Error, null);
          tokenStorage.clearTokens();
          // Emit event for auth state change
          window.dispatchEvent(new CustomEvent('auth:logout'));
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

      // Handle other errors
      return Promise.reject(error);
    }
  );

  return client;
}

// =============================================================================
// API Client Instance
// =============================================================================

export const apiClient = createApiClient();

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Extract error message from API error response
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiError>;
    // Try to get detail from response body
    if (axiosError.response?.data?.detail) {
      return axiosError.response.data.detail;
    }
    // Fall back to status text
    if (axiosError.response?.statusText) {
      return axiosError.response.statusText;
    }
    // Fall back to error message
    if (axiosError.message) {
      return axiosError.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unknown error occurred';
}

/**
 * Check if error is an authentication error
 */
export function isAuthError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    return error.response?.status === 401 || error.response?.status === 403;
  }
  return false;
}

/**
 * Check if error is a network error
 */
export function isNetworkError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    return !error.response && error.code === 'ERR_NETWORK';
  }
  return false;
}

/**
 * Check if the user is authenticated
 */
export function isAuthenticated(): boolean {
  const token = tokenStorage.getAccessToken();
  if (!token) return false;
  return !tokenStorage.isTokenExpired();
}

// =============================================================================
// Type-safe request helpers
// =============================================================================

/**
 * Make a GET request with type safety
 */
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await apiClient.get<T>(url, { params });
  return response.data;
}

/**
 * Make a POST request with type safety
 */
export async function post<T, D = unknown>(url: string, data?: D): Promise<T> {
  const response = await apiClient.post<T>(url, data);
  return response.data;
}

/**
 * Make a PUT request with type safety
 */
export async function put<T, D = unknown>(url: string, data?: D): Promise<T> {
  const response = await apiClient.put<T>(url, data);
  return response.data;
}

/**
 * Make a PATCH request with type safety
 */
export async function patch<T, D = unknown>(url: string, data?: D): Promise<T> {
  const response = await apiClient.patch<T>(url, data);
  return response.data;
}

/**
 * Make a DELETE request with type safety
 */
export async function del<T = void>(url: string): Promise<T> {
  const response = await apiClient.delete<T>(url);
  return response.data;
}

export default apiClient;
