import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  createdAt: string;
  updatedAt: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isLoading: boolean;
  error: string | null;
  rememberMe: boolean;
}

interface AuthActions {
  setUser: (user: User | null) => void;
  setTokens: (tokens: AuthTokens | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  setRememberMe: (rememberMe: boolean) => void;
  login: (user: User, tokens: AuthTokens) => void;
  logout: () => void;
  clearError: () => void;
  isAuthenticated: () => boolean;
  getAccessToken: () => string | null;
}

type AuthStore = AuthState & AuthActions;

const initialState: AuthState = {
  user: null,
  tokens: null,
  isLoading: false,
  error: null,
  rememberMe: false,
};

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setUser: (user) => set({ user }),

      setTokens: (tokens) => set({ tokens }),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error }),

      setRememberMe: (rememberMe) => set({ rememberMe }),

      login: (user, tokens) =>
        set({
          user,
          tokens,
          isLoading: false,
          error: null,
        }),

      logout: () =>
        set({
          user: null,
          tokens: null,
          error: null,
        }),

      clearError: () => set({ error: null }),

      isAuthenticated: () => {
        const { tokens, user } = get();
        return !!(tokens?.accessToken && user);
      },

      getAccessToken: () => {
        const { tokens } = get();
        return tokens?.accessToken ?? null;
      },
    }),
    {
      name: 'garageswarm-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        rememberMe: state.rememberMe,
      }),
    }
  )
);

// Selectors for optimized re-renders
export const selectUser = (state: AuthStore) => state.user;
export const selectTokens = (state: AuthStore) => state.tokens;
export const selectIsLoading = (state: AuthStore) => state.isLoading;
export const selectError = (state: AuthStore) => state.error;
export const selectIsAuthenticated = (state: AuthStore) => state.isAuthenticated();
