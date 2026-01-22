/**
 * Services Index
 *
 * Central export point for all API services.
 */

// =============================================================================
// Base API Client
// =============================================================================

export {
  apiClient,
  tokenStorage,
  getErrorMessage,
  isAuthError,
  isNetworkError,
  isAuthenticated,
  get,
  post,
  put,
  patch,
  del,
} from './api';

export type { TokenStorage } from './api';

// =============================================================================
// Authentication Service
// =============================================================================

export {
  authService,
  login,
  register,
  logout,
  refreshToken,
  getCurrentUser,
  changePassword,
  isAuthenticated as isUserAuthenticated,
} from './auth';

// =============================================================================
// Tasks Service
// =============================================================================

export {
  tasksService,
  getTasks,
  getTask,
  createTask,
  updateTask,
  deleteTask,
  cancelTask,
  assignTask,
} from './tasks';

// =============================================================================
// Workers Service
// =============================================================================

export {
  workersService,
  getWorkers,
  getWorker,
  registerWorker,
  updateWorker,
  getWorkerMetrics,
  sendHeartbeat,
  pullTask,
} from './workers';

// =============================================================================
// Workflows Service
// =============================================================================

export {
  workflowsService,
  getWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  startWorkflow,
  pauseWorkflow,
  resumeWorkflow,
  cancelWorkflow,
  getTemplates,
  createFromTemplate,
  getExecutionGraph,
  submitReview,
} from './workflows';

// =============================================================================
// MCP Service
// =============================================================================

export {
  mcpService,
  getMCPHealth,
  getServers,
  getServer,
  registerServer,
  unregisterServer,
  reconnectServer,
  getTools,
  getTool,
  invokeTool,
} from './mcp';

// =============================================================================
// WebSocket Service
// =============================================================================

export {
  websocketService,
  getWebSocketUrl,
  createWebSocketConnection,
} from './websocket';

export type { WebSocketConfig } from './websocket';

// =============================================================================
// Default Exports (Service Instances)
// =============================================================================

import apiClient from './api';
import authService from './auth';
import tasksService from './tasks';
import workersService from './workers';
import workflowsService from './workflows';
import mcpService from './mcp';
import websocketService from './websocket';

/**
 * All services bundled together
 */
export const services = {
  api: apiClient,
  auth: authService,
  tasks: tasksService,
  workers: workersService,
  workflows: workflowsService,
  mcp: mcpService,
  websocket: websocketService,
} as const;

export default services;
