/**
 * Test Utilities
 *
 * Custom render functions and utilities for testing React components.
 */

import React, { ReactElement, ReactNode } from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// =============================================================================
// Query Client for Tests
// =============================================================================

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// =============================================================================
// Providers
// =============================================================================

interface ProvidersProps {
  children: ReactNode;
}

function AllProviders({ children }: ProvidersProps): ReactElement {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

// =============================================================================
// Custom Render Functions
// =============================================================================

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  route?: string;
  initialEntries?: string[];
}

/**
 * Renders a component with all providers (QueryClient, Router, etc.)
 */
function customRender(
  ui: ReactElement,
  options?: CustomRenderOptions
): RenderResult & { user: ReturnType<typeof userEvent.setup> } {
  const user = userEvent.setup();

  const Wrapper = ({ children }: { children: ReactNode }) => {
    const queryClient = createTestQueryClient();

    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };

  return {
    user,
    ...render(ui, { wrapper: Wrapper, ...options }),
  };
}

/**
 * Renders a component with MemoryRouter for testing specific routes
 */
function renderWithRoute(
  ui: ReactElement,
  { route = '/', initialEntries = [route], ...options }: CustomRenderOptions = {}
): RenderResult & { user: ReturnType<typeof userEvent.setup> } {
  const user = userEvent.setup();

  const Wrapper = ({ children }: { children: ReactNode }) => {
    const queryClient = createTestQueryClient();

    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };

  return {
    user,
    ...render(ui, { wrapper: Wrapper, ...options }),
  };
}

/**
 * Renders a component within specific route context
 */
function renderWithRoutes(
  routes: ReactElement,
  { initialEntries = ['/'], ...options }: CustomRenderOptions = {}
): RenderResult & { user: ReturnType<typeof userEvent.setup> } {
  const user = userEvent.setup();

  const Wrapper = ({ children }: { children: ReactNode }) => {
    const queryClient = createTestQueryClient();

    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };

  return {
    user,
    ...render(<Routes>{routes}</Routes>, { wrapper: Wrapper, ...options }),
  };
}

// =============================================================================
// Wait Helpers
// =============================================================================

/**
 * Waits for a specified duration
 */
function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Flushes pending promises (useful for testing async effects)
 */
async function flushPromises(): Promise<void> {
  await wait(0);
}

// =============================================================================
// Mock Helpers
// =============================================================================

/**
 * Creates a mock implementation that returns different values on subsequent calls
 */
function createSequenceMock<T>(...values: T[]): () => T {
  let callCount = 0;
  return () => {
    const value = values[callCount % values.length];
    callCount++;
    return value;
  };
}

// =============================================================================
// Exports
// =============================================================================

export * from '@testing-library/react';
export { userEvent };
export {
  customRender as render,
  renderWithRoute,
  renderWithRoutes,
  createTestQueryClient,
  AllProviders,
  wait,
  flushPromises,
  createSequenceMock,
};
