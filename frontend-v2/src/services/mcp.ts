/**
 * MCP (Model Context Protocol) API Service
 *
 * Handles MCP server management, tool discovery, and tool invocation.
 */

import { get, post, del } from './api';
import type {
  MCPServerRegisterRequest,
  MCPServerStatusResponse,
  MCPBusHealthResponse,
  MCPToolDefinition,
  MCPToolListResponse,
  MCPToolInvokeRequest,
  MCPToolInvokeResponse,
} from '../types/api';

// =============================================================================
// API Endpoints
// =============================================================================

const MCP_ENDPOINTS = {
  HEALTH: '/mcp/health',
  SERVERS: '/mcp/servers',
  SERVER_BY_NAME: (name: string) => `/mcp/servers/${name}`,
  SERVER_RECONNECT: (name: string) => `/mcp/servers/${name}/reconnect`,
  SERVER_TOOLS: (name: string) => `/mcp/servers/${name}/tools`,
  TOOLS: '/mcp/tools',
  TOOL_BY_PATH: (path: string) => `/mcp/tools/${path}`,
  INVOKE: '/mcp/tools/invoke',
} as const;

// =============================================================================
// MCP Service
// =============================================================================

/**
 * MCP service class for managing MCP servers and tools
 */
class MCPService {
  // =========================================================================
  // Health & Status
  // =========================================================================

  /**
   * Get MCP Bus health status
   *
   * Returns overall health including connected servers and available tools.
   *
   * @returns MCP Bus health information
   */
  async getMCPHealth(): Promise<MCPBusHealthResponse> {
    return get<MCPBusHealthResponse>(MCP_ENDPOINTS.HEALTH);
  }

  // =========================================================================
  // Server Management
  // =========================================================================

  /**
   * Get all registered MCP servers
   *
   * @returns List of server status responses
   */
  async getServers(): Promise<MCPServerStatusResponse[]> {
    return get<MCPServerStatusResponse[]>(MCP_ENDPOINTS.SERVERS);
  }

  /**
   * Get status of a specific MCP server
   *
   * @param name - Server name
   * @returns Server status
   */
  async getServer(name: string): Promise<MCPServerStatusResponse> {
    return get<MCPServerStatusResponse>(MCP_ENDPOINTS.SERVER_BY_NAME(name));
  }

  /**
   * Register a new MCP server
   *
   * @param data - Server configuration
   * @returns Registered server status
   */
  async registerServer(data: MCPServerRegisterRequest): Promise<MCPServerStatusResponse> {
    return post<MCPServerStatusResponse>(MCP_ENDPOINTS.SERVERS, data);
  }

  /**
   * Unregister an MCP server
   *
   * @param name - Server name to unregister
   */
  async unregisterServer(name: string): Promise<void> {
    await del(MCP_ENDPOINTS.SERVER_BY_NAME(name));
  }

  /**
   * Reconnect to an MCP server
   *
   * Useful when a server connection has been lost.
   *
   * @param name - Server name to reconnect
   * @returns Updated server status
   */
  async reconnectServer(name: string): Promise<MCPServerStatusResponse> {
    return post<MCPServerStatusResponse>(MCP_ENDPOINTS.SERVER_RECONNECT(name));
  }

  // =========================================================================
  // Tool Management
  // =========================================================================

  /**
   * Get all available MCP tools
   *
   * @param serverName - Optional server name to filter tools
   * @returns List of available tools
   */
  async getTools(serverName?: string): Promise<MCPToolListResponse> {
    const params: Record<string, unknown> = {};
    if (serverName) {
      params.server_name = serverName;
    }
    return get<MCPToolListResponse>(MCP_ENDPOINTS.TOOLS, params);
  }

  /**
   * Get details of a specific tool
   *
   * @param toolPath - Full tool path (server.tool_name)
   * @returns Tool definition
   */
  async getTool(toolPath: string): Promise<MCPToolDefinition> {
    return get<MCPToolDefinition>(MCP_ENDPOINTS.TOOL_BY_PATH(toolPath));
  }

  /**
   * Invoke an MCP tool
   *
   * @param toolPath - Full tool path (server.tool_name)
   * @param args - Tool arguments
   * @param timeout - Optional timeout override in seconds
   * @returns Tool invocation result
   */
  async invokeTool(
    toolPath: string,
    args: Record<string, unknown> = {},
    timeout?: number
  ): Promise<MCPToolInvokeResponse> {
    const data: MCPToolInvokeRequest = {
      tool_path: toolPath,
      arguments: args,
      timeout,
    };
    return post<MCPToolInvokeResponse>(MCP_ENDPOINTS.INVOKE, data);
  }

  /**
   * Manually register a tool for a server
   *
   * This is useful for adding tools that weren't auto-discovered.
   *
   * @param serverName - Server to register the tool for
   * @param tool - Tool definition
   */
  async registerTool(
    serverName: string,
    tool: Omit<MCPToolDefinition, 'server'>
  ): Promise<{ status: string; tool: string }> {
    return post<{ status: string; tool: string }>(
      MCP_ENDPOINTS.SERVER_TOOLS(serverName),
      tool
    );
  }

  // =========================================================================
  // Convenience Methods
  // =========================================================================

  /**
   * Check if MCP Bus is healthy
   */
  async isHealthy(): Promise<boolean> {
    try {
      const health = await this.getMCPHealth();
      return health.bus_running;
    } catch {
      return false;
    }
  }

  /**
   * Get connected servers only
   */
  async getConnectedServers(): Promise<MCPServerStatusResponse[]> {
    const servers = await this.getServers();
    return servers.filter((s) => s.connected);
  }

  /**
   * Get disconnected servers
   */
  async getDisconnectedServers(): Promise<MCPServerStatusResponse[]> {
    const servers = await this.getServers();
    return servers.filter((s) => !s.connected);
  }

  /**
   * Get tools for a specific server
   */
  async getServerTools(serverName: string): Promise<MCPToolDefinition[]> {
    const response = await this.getTools(serverName);
    return response.tools;
  }

  /**
   * Register a STDIO-based MCP server
   */
  async registerStdioServer(
    name: string,
    command: string,
    args: string[] = [],
    env: Record<string, string> = {},
    timeout = 60
  ): Promise<MCPServerStatusResponse> {
    return this.registerServer({
      name,
      transport: 'stdio',
      command,
      args,
      env,
      timeout,
    });
  }

  /**
   * Register an SSE-based MCP server
   */
  async registerSseServer(
    name: string,
    url: string,
    timeout = 60
  ): Promise<MCPServerStatusResponse> {
    return this.registerServer({
      name,
      transport: 'sse',
      url,
      timeout,
    });
  }

  /**
   * Quick invoke with just tool path and args
   */
  async quickInvoke(
    toolPath: string,
    args: Record<string, unknown>
  ): Promise<unknown> {
    const result = await this.invokeTool(toolPath, args);
    if (result.status === 'error') {
      throw new Error(result.error || 'Tool invocation failed');
    }
    return result.result;
  }

  /**
   * Search tools by name or description
   */
  async searchTools(query: string): Promise<MCPToolDefinition[]> {
    const response = await this.getTools();
    const lowerQuery = query.toLowerCase();
    return response.tools.filter(
      (t) =>
        t.name.toLowerCase().includes(lowerQuery) ||
        t.description.toLowerCase().includes(lowerQuery)
    );
  }

  /**
   * Get a summary of all MCP resources
   */
  async getSummary(): Promise<{
    health: MCPBusHealthResponse;
    servers: MCPServerStatusResponse[];
    tools: MCPToolListResponse;
  }> {
    const [health, servers, tools] = await Promise.all([
      this.getMCPHealth(),
      this.getServers(),
      this.getTools(),
    ]);
    return { health, servers, tools };
  }
}

// =============================================================================
// Export Singleton Instance
// =============================================================================

export const mcpService = new MCPService();

// Export individual functions for convenience
export const getMCPHealth = mcpService.getMCPHealth.bind(mcpService);
export const getServers = mcpService.getServers.bind(mcpService);
export const getServer = mcpService.getServer.bind(mcpService);
export const registerServer = mcpService.registerServer.bind(mcpService);
export const unregisterServer = mcpService.unregisterServer.bind(mcpService);
export const reconnectServer = mcpService.reconnectServer.bind(mcpService);
export const getTools = mcpService.getTools.bind(mcpService);
export const getTool = mcpService.getTool.bind(mcpService);
export const invokeTool = mcpService.invokeTool.bind(mcpService);

export default mcpService;
