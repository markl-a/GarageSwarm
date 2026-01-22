/**
 * Authentication API Service
 *
 * Handles user authentication, registration, and token management.
 */

import { post, get } from './api';
import { tokenStorage } from './api';
import type {
  UserRegisterRequest,
  UserLoginRequest,
  TokenResponse,
  RefreshTokenRequest,
  ChangePasswordRequest,
  UserResponse,
} from '../types/api';

// =============================================================================
// API Endpoints
// =============================================================================

const AUTH_ENDPOINTS = {
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
  LOGOUT: '/auth/logout',
  REFRESH: '/auth/refresh',
  ME: '/auth/me',
  CHANGE_PASSWORD: '/auth/change-password',
} as const;

// =============================================================================
// Authentication Service
// =============================================================================

/**
 * Authentication service class for managing user auth state
 */
class AuthService {
  /**
   * Register a new user account
   *
   * @param email - User email address
   * @param password - User password (min 8 chars, must contain upper, lower, digit)
   * @param username - Username (alphanumeric, underscore, hyphen only)
   * @returns The created user information
   */
  async register(
    email: string,
    password: string,
    username: string
  ): Promise<UserResponse> {
    const data: UserRegisterRequest = {
      email,
      password,
      username,
    };
    return post<UserResponse>(AUTH_ENDPOINTS.REGISTER, data);
  }

  /**
   * Authenticate user and store tokens
   *
   * @param username - Username or email
   * @param password - User password
   * @returns Token response with access and refresh tokens
   */
  async login(username: string, password: string): Promise<TokenResponse> {
    const data: UserLoginRequest = {
      username,
      password,
    };
    const response = await post<TokenResponse>(AUTH_ENDPOINTS.LOGIN, data);

    // Store tokens in local storage
    tokenStorage.setTokens(response);

    // Emit auth state change event
    window.dispatchEvent(new CustomEvent('auth:login', { detail: response }));

    return response;
  }

  /**
   * Logout current user and invalidate tokens
   *
   * Blacklists the refresh token on the server and clears local storage.
   */
  async logout(): Promise<void> {
    const refreshToken = tokenStorage.getRefreshToken();

    if (refreshToken) {
      try {
        const data: RefreshTokenRequest = {
          refresh_token: refreshToken,
        };
        await post<void>(AUTH_ENDPOINTS.LOGOUT, data);
      } catch (error) {
        // Ignore errors during logout - still clear local tokens
        console.warn('Logout request failed, clearing tokens anyway:', error);
      }
    }

    // Clear tokens from storage
    tokenStorage.clearTokens();

    // Emit auth state change event
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }

  /**
   * Refresh the access token using the refresh token
   *
   * @returns New token response
   * @throws Error if refresh token is invalid or expired
   */
  async refreshToken(): Promise<TokenResponse> {
    const refreshToken = tokenStorage.getRefreshToken();

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const data: RefreshTokenRequest = {
      refresh_token: refreshToken,
    };

    const response = await post<TokenResponse>(AUTH_ENDPOINTS.REFRESH, data);

    // Store new tokens
    tokenStorage.setTokens(response);

    return response;
  }

  /**
   * Get the current authenticated user's information
   *
   * @returns Current user data
   * @throws Error if not authenticated
   */
  async getCurrentUser(): Promise<UserResponse> {
    return get<UserResponse>(AUTH_ENDPOINTS.ME);
  }

  /**
   * Change the current user's password
   *
   * @param currentPassword - The user's current password
   * @param newPassword - The new password (min 8 chars, must contain upper, lower, digit)
   */
  async changePassword(
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    const data: ChangePasswordRequest = {
      current_password: currentPassword,
      new_password: newPassword,
    };
    await post<void>(AUTH_ENDPOINTS.CHANGE_PASSWORD, data);
  }

  /**
   * Check if user is currently authenticated
   *
   * @returns true if user has a valid (non-expired) access token
   */
  isAuthenticated(): boolean {
    const token = tokenStorage.getAccessToken();
    if (!token) return false;
    return !tokenStorage.isTokenExpired();
  }

  /**
   * Check if the access token needs refresh
   *
   * @returns true if token is expired or will expire soon
   */
  needsRefresh(): boolean {
    return tokenStorage.isTokenExpired();
  }

  /**
   * Get the current access token
   *
   * @returns The access token or null if not authenticated
   */
  getAccessToken(): string | null {
    return tokenStorage.getAccessToken();
  }

  /**
   * Get the current refresh token
   *
   * @returns The refresh token or null if not available
   */
  getRefreshToken(): string | null {
    return tokenStorage.getRefreshToken();
  }
}

// =============================================================================
// Export Singleton Instance
// =============================================================================

export const authService = new AuthService();

// Export individual functions for convenience
export const login = authService.login.bind(authService);
export const register = authService.register.bind(authService);
export const logout = authService.logout.bind(authService);
export const refreshToken = authService.refreshToken.bind(authService);
export const getCurrentUser = authService.getCurrentUser.bind(authService);
export const changePassword = authService.changePassword.bind(authService);
export const isAuthenticated = authService.isAuthenticated.bind(authService);

export default authService;
