"""
GarageSwarm MCP (Model Context Protocol) Module

This module provides the MCP infrastructure for integrating various AI tools
(Claude Code, Gemini CLI, Ollama, etc.) through a unified interface.

Components:
- MCPBus: Central manager for MCP server connections and tool invocations
- ToolRegistry: Registry for discovering and managing available tools
- Servers: MCP server wrappers for different AI tools
- Transports: Communication layers (STDIO, SSE)

Usage:
    from backend.src.mcp import get_mcp_bus, create_mcp_bus

    # Get singleton instance
    bus = get_mcp_bus()
    await bus.start()

    # Register a server
    from backend.src.mcp.types import MCPServerConfig
    await bus.register_server("ollama", MCPServerConfig(
        transport="stdio",
        command="ollama-mcp"
    ))

    # Invoke a tool
    result = await bus.invoke_tool("ollama.generate", {"prompt": "Hello!"})
"""

from .bus import MCPBus, create_mcp_bus, get_mcp_bus
from .registry import ToolRegistry
from .types import (
    MCPError,
    MCPErrorCode,
    MCPMessage,
    MCPMessageType,
    MCPServerConfig,
    MCPServerStatus,
    MCPTransport,
    ServerInfo,
    ToolDefinition,
    ToolInvocation,
    ToolResult,
    ToolResultStatus,
)

__all__ = [
    # Bus
    "MCPBus",
    "get_mcp_bus",
    "create_mcp_bus",
    # Registry
    "ToolRegistry",
    # Types
    "MCPError",
    "MCPErrorCode",
    "MCPMessage",
    "MCPMessageType",
    "MCPServerConfig",
    "MCPServerStatus",
    "MCPTransport",
    "ServerInfo",
    "ToolDefinition",
    "ToolInvocation",
    "ToolResult",
    "ToolResultStatus",
]

__version__ = "0.1.0"
