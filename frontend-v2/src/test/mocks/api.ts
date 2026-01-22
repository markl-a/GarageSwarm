/**
 * API Mocks for Testing
 *
 * Mock API responses and MSW handlers for testing API integrations.
 */

import { http, HttpResponse } from 'msw';
import type {
  UserResponse,
  TokenResponse,
  TaskResponse,
  TaskListResponse,
  WorkerResponse,
  WorkerListResponse,
  WorkflowResponse,
  WorkflowListResponse,
} from '@/types/api';
import type { DashboardStats } from '@/types/dashboard';

// =============================================================================
// Base URL
// =============================================================================

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// =============================================================================
// Mock Data
// =============================================================================

export const mockUser: UserResponse = {
  user_id: 'user-123',
  username: 'testuser',
  email: 'test@example.com',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  last_login: '2024-01-15T10:00:00Z',
};

export const mockTokens: TokenResponse = {
  access_token: 'mock-access-token-12345',
  refresh_token: 'mock-refresh-token-67890',
  token_type: 'Bearer',
  expires_in: 3600,
};

export const mockTasks: TaskResponse[] = [
  {
    task_id: 'task-1',
    user_id: 'user-123',
    worker_id: 'worker-1',
    workflow_id: null,
    description: 'Test task 1',
    status: 'completed',
    progress: 100,
    priority: 1,
    tool_preference: 'claude_code',
    result: { output: 'Task completed successfully' },
    error: null,
    created_at: '2024-01-10T09:00:00Z',
    updated_at: '2024-01-10T09:30:00Z',
    started_at: '2024-01-10T09:05:00Z',
    completed_at: '2024-01-10T09:30:00Z',
  },
  {
    task_id: 'task-2',
    user_id: 'user-123',
    worker_id: null,
    workflow_id: null,
    description: 'Test task 2',
    status: 'pending',
    progress: 0,
    priority: 2,
    tool_preference: 'gemini_cli',
    result: null,
    error: null,
    created_at: '2024-01-11T10:00:00Z',
    updated_at: '2024-01-11T10:00:00Z',
    started_at: null,
    completed_at: null,
  },
  {
    task_id: 'task-3',
    user_id: 'user-123',
    worker_id: 'worker-2',
    workflow_id: null,
    description: 'Test task 3',
    status: 'running',
    progress: 50,
    priority: 1,
    tool_preference: null,
    result: null,
    error: null,
    created_at: '2024-01-12T11:00:00Z',
    updated_at: '2024-01-12T11:15:00Z',
    started_at: '2024-01-12T11:05:00Z',
    completed_at: null,
  },
];

export const mockWorkers: WorkerResponse[] = [
  {
    worker_id: 'worker-1',
    machine_id: 'machine-abc',
    machine_name: 'Worker Desktop 1',
    status: 'online',
    tools: ['claude_code', 'gemini_cli'],
    system_info: { os: 'Windows', cpu: 'Intel i7' },
    cpu_percent: 45.5,
    memory_percent: 62.3,
    disk_percent: 35.0,
    last_heartbeat: '2024-01-15T10:00:00Z',
    registered_at: '2024-01-01T00:00:00Z',
  },
  {
    worker_id: 'worker-2',
    machine_id: 'machine-def',
    machine_name: 'Worker Docker 1',
    status: 'busy',
    tools: ['ollama'],
    system_info: { os: 'Linux', cpu: 'AMD Ryzen' },
    cpu_percent: 85.2,
    memory_percent: 78.1,
    disk_percent: 50.0,
    last_heartbeat: '2024-01-15T10:00:00Z',
    registered_at: '2024-01-02T00:00:00Z',
  },
  {
    worker_id: 'worker-3',
    machine_id: 'machine-ghi',
    machine_name: 'Worker Desktop 2',
    status: 'offline',
    tools: ['claude_code'],
    system_info: { os: 'macOS', cpu: 'Apple M1' },
    cpu_percent: null,
    memory_percent: null,
    disk_percent: null,
    last_heartbeat: '2024-01-14T18:00:00Z',
    registered_at: '2024-01-03T00:00:00Z',
  },
];

export const mockWorkflows: WorkflowResponse[] = [
  {
    workflow_id: 'workflow-1',
    user_id: 'user-123',
    name: 'Test Workflow',
    description: 'A test workflow for testing',
    workflow_type: 'sequential',
    status: 'running',
    dag_definition: null,
    context: {},
    result: null,
    error: null,
    total_nodes: 5,
    completed_nodes: 2,
    progress: 40,
    created_at: '2024-01-10T00:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    started_at: '2024-01-15T09:00:00Z',
    completed_at: null,
  },
];

export const mockDashboardStats: DashboardStats = {
  totalTasks: 150,
  totalWorkers: 10,
  totalWorkflows: 25,
  activeTasks: 5,
  activeWorkers: 7,
  activeWorkflows: 3,
  completedTasksToday: 20,
  failedTasksToday: 2,
};

// =============================================================================
// MSW Handlers
// =============================================================================

export const handlers = [
  // Authentication
  http.post(`${API_BASE_URL}/auth/login`, async ({ request }) => {
    const body = await request.json() as { username?: string; email?: string; password: string };

    if ((body.username === 'testuser' || body.email === 'test@example.com') && body.password === 'password123') {
      return HttpResponse.json({
        user: mockUser,
        tokens: mockTokens,
      });
    }

    return HttpResponse.json(
      { detail: 'Invalid credentials' },
      { status: 401 }
    );
  }),

  http.post(`${API_BASE_URL}/auth/register`, async ({ request }) => {
    const body = await request.json() as { username: string; email: string; password: string };

    if (body.email === 'existing@example.com') {
      return HttpResponse.json(
        { detail: 'Email already registered' },
        { status: 400 }
      );
    }

    return HttpResponse.json({
      user: { ...mockUser, username: body.username, email: body.email },
      tokens: mockTokens,
    });
  }),

  http.post(`${API_BASE_URL}/auth/logout`, () => {
    return HttpResponse.json({ message: 'Logged out successfully' });
  }),

  http.post(`${API_BASE_URL}/auth/refresh`, async ({ request }) => {
    const body = await request.json() as { refresh_token: string };

    if (body.refresh_token === 'mock-refresh-token-67890') {
      return HttpResponse.json({
        access_token: 'new-mock-access-token',
        refresh_token: 'new-mock-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
      });
    }

    return HttpResponse.json(
      { detail: 'Invalid refresh token' },
      { status: 401 }
    );
  }),

  http.get(`${API_BASE_URL}/auth/me`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (authHeader && authHeader.startsWith('Bearer ')) {
      return HttpResponse.json(mockUser);
    }

    return HttpResponse.json(
      { detail: 'Not authenticated' },
      { status: 401 }
    );
  }),

  // Tasks
  http.get(`${API_BASE_URL}/tasks`, () => {
    const response: TaskListResponse = {
      tasks: mockTasks,
      total: mockTasks.length,
      limit: 20,
      offset: 0,
    };
    return HttpResponse.json(response);
  }),

  http.get(`${API_BASE_URL}/tasks/:taskId`, ({ params }) => {
    const task = mockTasks.find((t) => t.task_id === params.taskId);

    if (task) {
      return HttpResponse.json(task);
    }

    return HttpResponse.json(
      { detail: 'Task not found' },
      { status: 404 }
    );
  }),

  http.post(`${API_BASE_URL}/tasks`, async ({ request }) => {
    const body = await request.json() as { description: string };

    const newTask: TaskResponse = {
      task_id: `task-${Date.now()}`,
      user_id: 'user-123',
      worker_id: null,
      workflow_id: null,
      description: body.description,
      status: 'pending',
      progress: 0,
      priority: 1,
      tool_preference: null,
      result: null,
      error: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      started_at: null,
      completed_at: null,
    };

    return HttpResponse.json(newTask, { status: 201 });
  }),

  // Workers
  http.get(`${API_BASE_URL}/workers`, () => {
    const response: WorkerListResponse = {
      workers: mockWorkers,
      total: mockWorkers.length,
      limit: 20,
      offset: 0,
    };
    return HttpResponse.json(response);
  }),

  http.get(`${API_BASE_URL}/workers/:workerId`, ({ params }) => {
    const worker = mockWorkers.find((w) => w.worker_id === params.workerId);

    if (worker) {
      return HttpResponse.json(worker);
    }

    return HttpResponse.json(
      { detail: 'Worker not found' },
      { status: 404 }
    );
  }),

  // Workflows
  http.get(`${API_BASE_URL}/workflows`, () => {
    const response: WorkflowListResponse = {
      workflows: mockWorkflows,
      total: mockWorkflows.length,
      limit: 20,
      offset: 0,
    };
    return HttpResponse.json(response);
  }),

  http.get(`${API_BASE_URL}/workflows/:workflowId`, ({ params }) => {
    const workflow = mockWorkflows.find((w) => w.workflow_id === params.workflowId);

    if (workflow) {
      return HttpResponse.json(workflow);
    }

    return HttpResponse.json(
      { detail: 'Workflow not found' },
      { status: 404 }
    );
  }),

  // Dashboard
  http.get(`${API_BASE_URL}/dashboard/stats`, () => {
    return HttpResponse.json(mockDashboardStats);
  }),
];

// =============================================================================
// Error Handlers
// =============================================================================

export const errorHandlers = {
  networkError: http.get(`${API_BASE_URL}/*`, () => {
    return HttpResponse.error();
  }),

  serverError: http.get(`${API_BASE_URL}/*`, () => {
    return HttpResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }),

  unauthorized: http.get(`${API_BASE_URL}/*`, () => {
    return HttpResponse.json(
      { detail: 'Not authenticated' },
      { status: 401 }
    );
  }),
};

export default handlers;
