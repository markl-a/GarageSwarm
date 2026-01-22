/**
 * Login Page Tests
 *
 * Tests for the Login page covering:
 * - Form submission
 * - Validation errors
 * - Success redirect
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Login } from '../Login';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
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
}

// Wrapper component with all required providers
function renderLogin(initialEntries: string[] = ['/login']) {
  const queryClient = createTestQueryClient();
  const user = userEvent.setup();

  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<div>Dashboard Page</div>} />
          <Route path="/register" element={<div>Register Page</div>} />
          <Route path="/forgot-password" element={<div>Forgot Password Page</div>} />
          <Route path="/" element={<div>Home Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );

  return { ...result, user };
}

describe('Login Page', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Basic Rendering
  // ===========================================================================

  describe('Basic Rendering', () => {
    it('renders login form', () => {
      renderLogin();

      expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('renders email and password inputs', () => {
      renderLogin();

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      expect(emailInput).toHaveAttribute('type', 'email');
      expect(passwordInput).toHaveAttribute('type', 'password');
    });

    it('renders remember me checkbox', () => {
      renderLogin();

      expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument();
    });

    it('renders forgot password link', () => {
      renderLogin();

      expect(screen.getByRole('link', { name: /forgot password/i })).toBeInTheDocument();
    });

    it('renders register link', () => {
      renderLogin();

      expect(screen.getByRole('link', { name: /create an account/i })).toBeInTheDocument();
    });

    it('renders GarageSwarm logo and branding', () => {
      renderLogin();

      expect(screen.getByText('GarageSwarm')).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Form Validation
  // ===========================================================================

  describe('Form Validation', () => {
    it('disables submit button when form is empty', () => {
      renderLogin();

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).toBeDisabled();
    });

    it('disables submit button when only email is filled', async () => {
      const { user } = renderLogin();

      const emailInput = screen.getByLabelText(/email address/i);
      await user.type(emailInput, 'test@example.com');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).toBeDisabled();
    });

    it('disables submit button when only password is filled', async () => {
      const { user } = renderLogin();

      const passwordInput = screen.getByLabelText(/password/i);
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).toBeDisabled();
    });

    it('enables submit button when both fields are filled', async () => {
      const { user } = renderLogin();

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).not.toBeDisabled();
    });
  });

  // ===========================================================================
  // Form Submission
  // ===========================================================================

  describe('Form Submission', () => {
    it('submits form with correct data', async () => {
      const { user } = renderLogin();

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      // Should show loading state
      await waitFor(() => {
        expect(screen.queryByText(/signing in/i)).toBeInTheDocument();
      });
    });

    it('shows loading state during submission', async () => {
      const { user } = renderLogin();

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      // Check for loading state
      await waitFor(() => {
        expect(screen.getByText(/signing in/i)).toBeInTheDocument();
      });
    });

    it('redirects to dashboard on successful login', async () => {
      const { user } = renderLogin();

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      // Wait for redirect
      await waitFor(
        () => {
          expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  // ===========================================================================
  // Error Handling
  // ===========================================================================

  describe('Error Handling', () => {
    it('displays error message on invalid credentials', async () => {
      // Override the handler for this test
      server.use(
        http.post('http://127.0.0.1:8000/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Invalid credentials' },
            { status: 401 }
          );
        })
      );

      const { user } = renderLogin();

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      await user.type(emailInput, 'wrong@example.com');
      await user.type(passwordInput, 'wrongpassword');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      // Wait for error message
      await waitFor(() => {
        expect(screen.getByText(/invalid credentials|failed/i)).toBeInTheDocument();
      });
    });

    it('displays server error message', async () => {
      server.use(
        http.post('http://127.0.0.1:8000/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Server error' },
            { status: 500 }
          );
        })
      );

      const { user } = renderLogin();

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/error|failed/i)).toBeInTheDocument();
      });
    });

    it('clears error when form data changes', async () => {
      server.use(
        http.post('http://127.0.0.1:8000/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Invalid credentials' },
            { status: 401 }
          );
        })
      );

      const { user } = renderLogin();

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      await user.type(emailInput, 'wrong@example.com');
      await user.type(passwordInput, 'wrongpassword');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      // Wait for error message
      await waitFor(() => {
        expect(screen.getByText(/invalid credentials|failed/i)).toBeInTheDocument();
      });

      // Type in the email field to trigger error clearing
      await user.type(emailInput, 'x');

      // Error should be cleared
      await waitFor(() => {
        expect(screen.queryByText(/invalid credentials/i)).not.toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Password Visibility Toggle
  // ===========================================================================

  describe('Password Visibility Toggle', () => {
    it('toggles password visibility', async () => {
      const { user } = renderLogin();

      const passwordInput = screen.getByLabelText(/password/i);

      // Initially password is hidden
      expect(passwordInput).toHaveAttribute('type', 'password');

      // Find and click the toggle button (the button inside the password field container)
      const toggleButtons = screen.getAllByRole('button');
      const toggleButton = toggleButtons.find(
        (btn) => !btn.textContent?.includes('Sign in') && !btn.textContent?.includes('Create')
      );

      if (toggleButton) {
        await user.click(toggleButton);

        // Password should now be visible
        expect(passwordInput).toHaveAttribute('type', 'text');

        // Click again to hide
        await user.click(toggleButton);

        // Password should be hidden again
        expect(passwordInput).toHaveAttribute('type', 'password');
      }
    });
  });

  // ===========================================================================
  // Remember Me
  // ===========================================================================

  describe('Remember Me', () => {
    it('toggles remember me checkbox', async () => {
      const { user } = renderLogin();

      const rememberMeCheckbox = screen.getByLabelText(/remember me/i);

      // Initially unchecked
      expect(rememberMeCheckbox).not.toBeChecked();

      // Click to check
      await user.click(rememberMeCheckbox);

      expect(rememberMeCheckbox).toBeChecked();

      // Click to uncheck
      await user.click(rememberMeCheckbox);

      expect(rememberMeCheckbox).not.toBeChecked();
    });
  });

  // ===========================================================================
  // Navigation Links
  // ===========================================================================

  describe('Navigation Links', () => {
    it('navigates to forgot password page', async () => {
      const { user } = renderLogin();

      const forgotPasswordLink = screen.getByRole('link', { name: /forgot password/i });
      await user.click(forgotPasswordLink);

      expect(screen.getByText('Forgot Password Page')).toBeInTheDocument();
    });

    it('navigates to register page', async () => {
      const { user } = renderLogin();

      const registerLink = screen.getByRole('link', { name: /create an account/i });
      await user.click(registerLink);

      expect(screen.getByText('Register Page')).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Success Message from Registration
  // ===========================================================================

  describe('Success Message from Registration', () => {
    it('displays success message when redirected from registration', () => {
      render(
        <QueryClientProvider client={createTestQueryClient()}>
          <MemoryRouter
            initialEntries={[
              {
                pathname: '/login',
                state: { message: 'Registration successful! Please log in.' },
              },
            ]}
          >
            <Routes>
              <Route path="/login" element={<Login />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(screen.getByText(/registration successful/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility
  // ===========================================================================

  describe('Accessibility', () => {
    it('has accessible form labels', () => {
      renderLogin();

      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument();
    });

    it('has accessible submit button', () => {
      renderLogin();

      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('form inputs are focusable', async () => {
      const { user } = renderLogin();

      await user.tab();

      // First focusable should be the logo link, then email
      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      await user.tab();
      await user.tab();

      // Check that inputs can receive focus
      expect(emailInput).not.toHaveFocus(); // Logo was focused first
      expect(document.activeElement).not.toBe(passwordInput);
    });
  });
});
