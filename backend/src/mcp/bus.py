"""
MCP Bus Manager

Core infrastructure for managing MCP server connections and tool invocations.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .registry import ToolNotFoundError, ToolRegistry
from .types import (
    MCPError,
    MCPErrorCode,
    MCPMessage,
    MCPMessageType,
    MCPServerConfig,
    MCPServerStatus,
    ServerInfo,
    ToolDefinition,
    ToolInvocation,
    ToolResult,
    ToolResultStatus,
)


logger = logging.getLogger(__name__)


class MCPBusError(Exception):
    """Base exception for MCP Bus errors."""
    pass


class ServerNotFoundError(MCPBusError):
    """Raised when a requested server is not found."""
    pass


class ServerConnectionError(MCPBusError):
    """Raised when server connection fails."""
    pass


class ToolInvocationError(MCPBusError):
    """Raised when tool invocation fails."""
    pass


class MCPBus:
    """
    MCP Bus Manager.

    Manages MCP server connections, tool registry, and tool invocations.
    Provides a unified interface for interacting with multiple MCP servers.
    """

    def __init__(self):
        """Initialize the MCP Bus."""
        self._servers: Dict[str, ServerInfo] = {}
        self._registry = ToolRegistry()
        self._connections: Dict[str, Any] = {}  # Server connections (transport-specific)
        self._invocations: Dict[str, ToolInvocation] = {}
        self._lock = asyncio.Lock()
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._running = False
        logger.info("MCPBus initialized")

    @property
    def registry(self) -> ToolRegistry:
        """Get the tool registry."""
        return self._registry

    async def start(self) -> None:
        """Start the MCP Bus."""
        if self._running:
            logger.warning("MCPBus is already running")
            return

        self._running = True
        logger.info("MCPBus started")
        await self._emit_event("bus_started", {})

    async def stop(self) -> None:
        """Stop the MCP Bus and disconnect all servers."""
        if not self._running:
            return

        self._running = False

        # Disconnect all servers
        server_names = list(self._servers.keys())
        for name in server_names:
            try:
                await self.unregister_server(name)
            except Exception as e:
                logger.error(f"Error unregistering server {name}: {e}")

        logger.info("MCPBus stopped")
        await self._emit_event("bus_stopped", {})

    async def register_server(
        self,
        name: str,
        config: MCPServerConfig,
        connect: bool = True
    ) -> ServerInfo:
        """
        Register an MCP server.

        Args:
            name: Unique name for the server
            config: Server configuration
            connect: Whether to connect immediately

        Returns:
            Server info object

        Raises:
            MCPBusError: If server already exists
        """
        async with self._lock:
            if name in self._servers:
                raise MCPBusError(f"Server '{name}' is already registered")

            # Ensure config has correct name
            config_data = config.model_dump()
            config_data["name"] = name
            config = MCPServerConfig(**config_data)

            server_info = ServerInfo(
                name=name,
                status=MCPServerStatus.DISCONNECTED,
                config=config,
                connected_at=None,
                last_heartbeat=None,
                tool_count=0
            )

            self._servers[name] = server_info
            logger.info(f"Registered server: {name}")

        if connect:
            await self._connect_server(name)

        await self._emit_event("server_registered", {"server": name})
        return self._servers[name]

    async def unregister_server(self, name: str) -> bool:
        """
        Unregister and disconnect an MCP server.

        Args:
            name: Server name

        Returns:
            True if server was unregistered

        Raises:
            ServerNotFoundError: If server is not found
        """
        if name not in self._servers:
            raise ServerNotFoundError(f"Server not found: {name}")

        # Disconnect first
        await self._disconnect_server(name)

        # Remove tools from registry
        await self._registry.unregister_server_tools(name)

        async with self._lock:
            del self._servers[name]
            if name in self._connections:
                del self._connections[name]

        logger.info(f"Unregistered server: {name}")
        await self._emit_event("server_unregistered", {"server": name})
        return True

    async def _connect_server(self, name: str) -> None:
        """
        Connect to an MCP server.

        Args:
            name: Server name

        Raises:
            ServerNotFoundError: If server is not found
            ServerConnectionError: If connection fails
        """
        if name not in self._servers:
            raise ServerNotFoundError(f"Server not found: {name}")

        server = self._servers[name]
        server.status = MCPServerStatus.CONNECTING

        try:
            # TODO: Implement transport-specific connection logic
            # For now, simulate successful connection
            config = server.config

            logger.info(
                f"Connecting to server '{name}' via {config.transport} transport"
            )

            # Simulate connection delay
            await asyncio.sleep(0.1)

            # Initialize the server (send initialize request)
            init_response = await self._send_initialize(name)

            if init_response:
                server.status = MCPServerStatus.CONNECTED
                server.connected_at = datetime.utcnow()
                server.last_heartbeat = datetime.utcnow()

                # Fetch and register tools
                await self._fetch_server_tools(name)

                logger.info(f"Connected to server: {name}")
                await self._emit_event("server_connected", {"server": name})
            else:
                raise ServerConnectionError(f"Failed to initialize server: {name}")

        except Exception as e:
            server.status = MCPServerStatus.ERROR
            server.error_message = str(e)
            logger.error(f"Failed to connect to server '{name}': {e}")
            raise ServerConnectionError(f"Connection failed: {e}")

    async def _disconnect_server(self, name: str) -> None:
        """
        Disconnect from an MCP server.

        Args:
            name: Server name
        """
        if name not in self._servers:
            return

        server = self._servers[name]

        try:
            # TODO: Implement transport-specific disconnection
            logger.info(f"Disconnecting from server: {name}")

            server.status = MCPServerStatus.DISCONNECTED
            server.connected_at = None

            await self._emit_event("server_disconnected", {"server": name})

        except Exception as e:
            logger.error(f"Error disconnecting from server '{name}': {e}")
            server.status = MCPServerStatus.ERROR
            server.error_message = str(e)

    async def _send_initialize(self, name: str) -> bool:
        """
        Send initialize request to server.

        Args:
            name: Server name

        Returns:
            True if initialization succeeded
        """
        # TODO: Implement actual MCP initialize handshake
        # For now, return True to simulate successful initialization
        message = MCPMessage(
            id=str(uuid.uuid4()),
            method=MCPMessageType.INITIALIZE,
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "GarageSwarm",
                    "version": "0.0.1"
                }
            }
        )

        logger.debug(f"Sending initialize to {name}: {message.model_dump()}")
        return True

    async def _fetch_server_tools(self, name: str) -> List[ToolDefinition]:
        """
        Fetch tools from a server and register them.

        Args:
            name: Server name

        Returns:
            List of fetched tool definitions
        """
        if name not in self._servers:
            return []

        server = self._servers[name]

        # TODO: Implement actual MCP tools/list request
        # For now, return empty list - tools will be added via register_tool
        message = MCPMessage(
            id=str(uuid.uuid4()),
            method=MCPMessageType.LIST_TOOLS,
            params={}
        )

        logger.debug(f"Fetching tools from {name}")

        # Simulate response - in reality this would come from the server
        tools: List[ToolDefinition] = []

        # Register fetched tools
        await self._registry.register_tools(name, tools, overwrite=True)
        server.tool_count = await self._registry.get_tool_count(name)

        return tools

    async def invoke_tool(
        self,
        tool_path: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> ToolResult:
        """
        Invoke an MCP tool.

        Args:
            tool_path: Full tool path (server.tool_name)
            arguments: Tool arguments
            timeout: Optional timeout in seconds

        Returns:
            Tool execution result

        Raises:
            ToolNotFoundError: If tool is not found
            ServerNotFoundError: If server is not connected
            ToolInvocationError: If invocation fails
        """
        start_time = time.time()
        arguments = arguments or {}

        # Parse tool path
        if "." not in tool_path:
            raise ToolInvocationError(
                f"Invalid tool path format: {tool_path}. Expected 'server.tool_name'"
            )

        server_name, tool_name = tool_path.split(".", 1)

        # Check server exists and is connected
        if server_name not in self._servers:
            raise ServerNotFoundError(f"Server not found: {server_name}")

        server = self._servers[server_name]
        if server.status != MCPServerStatus.CONNECTED:
            raise ServerNotFoundError(
                f"Server '{server_name}' is not connected (status: {server.status})"
            )

        # Get tool definition
        tool = await self._registry.get_tool(tool_path)

        # Create invocation record
        invocation_id = str(uuid.uuid4())
        invocation = ToolInvocation(
            id=invocation_id,
            tool_path=tool_path,
            arguments=arguments,
            started_at=datetime.utcnow()
        )
        self._invocations[invocation_id] = invocation

        logger.info(f"Invoking tool: {tool_path} (id: {invocation_id})")

        try:
            # Build MCP message
            message = MCPMessage(
                id=invocation_id,
                method=MCPMessageType.CALL_TOOL,
                params={
                    "name": tool_name,
                    "arguments": arguments
                }
            )

            # TODO: Send message via transport and get response
            # For now, simulate a placeholder response
            result_data = await self._execute_tool_call(
                server_name,
                tool,
                arguments,
                timeout
            )

            execution_time = time.time() - start_time

            result = ToolResult(
                tool_path=tool_path,
                status=ToolResultStatus.SUCCESS,
                result=result_data,
                execution_time=execution_time
            )

            invocation.completed_at = datetime.utcnow()
            invocation.result = result

            logger.info(
                f"Tool invocation completed: {tool_path} "
                f"(time: {execution_time:.2f}s)"
            )

            await self._emit_event("tool_invoked", {
                "tool_path": tool_path,
                "invocation_id": invocation_id,
                "status": "success"
            })

            return result

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            result = ToolResult(
                tool_path=tool_path,
                status=ToolResultStatus.TIMEOUT,
                error=f"Tool execution timed out after {timeout}s",
                execution_time=execution_time
            )
            invocation.completed_at = datetime.utcnow()
            invocation.result = result

            logger.warning(f"Tool invocation timed out: {tool_path}")
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            result = ToolResult(
                tool_path=tool_path,
                status=ToolResultStatus.ERROR,
                error=str(e),
                execution_time=execution_time
            )
            invocation.completed_at = datetime.utcnow()
            invocation.result = result

            logger.error(f"Tool invocation failed: {tool_path} - {e}")
            raise ToolInvocationError(f"Tool invocation failed: {e}")

    async def _execute_tool_call(
        self,
        server_name: str,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute a tool call on the server.

        Args:
            server_name: Server name
            tool: Tool definition
            arguments: Tool arguments
            timeout: Optional timeout

        Returns:
            Tool execution result
        """
        # TODO: Implement actual transport-based tool execution
        # This is a placeholder that should be replaced with real transport logic

        server = self._servers[server_name]
        config = server.config
        effective_timeout = timeout or config.timeout

        # Simulate tool execution
        await asyncio.sleep(0.05)

        # Return placeholder result
        return {
            "status": "executed",
            "tool": tool.name,
            "server": server_name,
            "arguments": arguments,
            "_note": "This is a placeholder. Implement transport layer for real execution."
        }

    async def get_available_tools(
        self,
        server_name: Optional[str] = None
    ) -> List[ToolDefinition]:
        """
        Get all available tools or tools from a specific server.

        Args:
            server_name: Optional server name to filter by

        Returns:
            List of tool definitions
        """
        return await self._registry.list_tools(server_name)

    async def get_server_status(self, name: str) -> ServerInfo:
        """
        Get status of an MCP server.

        Args:
            name: Server name

        Returns:
            Server info object

        Raises:
            ServerNotFoundError: If server is not found
        """
        if name not in self._servers:
            raise ServerNotFoundError(f"Server not found: {name}")
        return self._servers[name]

    async def get_all_servers(self) -> List[ServerInfo]:
        """
        Get info for all registered servers.

        Returns:
            List of server info objects
        """
        return list(self._servers.values())

    async def reconnect_server(self, name: str) -> bool:
        """
        Reconnect to a server.

        Args:
            name: Server name

        Returns:
            True if reconnection succeeded
        """
        if name not in self._servers:
            raise ServerNotFoundError(f"Server not found: {name}")

        await self._disconnect_server(name)
        await self._connect_server(name)

        return self._servers[name].status == MCPServerStatus.CONNECTED

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all servers.

        Returns:
            Health check results
        """
        results = {
            "bus_running": self._running,
            "total_servers": len(self._servers),
            "connected_servers": 0,
            "total_tools": len(self._registry),
            "servers": {}
        }

        for name, server in self._servers.items():
            is_connected = server.status == MCPServerStatus.CONNECTED
            if is_connected:
                results["connected_servers"] += 1

            results["servers"][name] = {
                "status": server.status,
                "connected": is_connected,
                "tool_count": server.tool_count,
                "connected_at": server.connected_at.isoformat() if server.connected_at else None,
                "error": server.error_message
            }

        return results

    def on(self, event: str, handler: Callable) -> None:
        """
        Register an event handler.

        Args:
            event: Event name
            handler: Async handler function
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> None:
        """
        Unregister an event handler.

        Args:
            event: Event name
            handler: Handler function to remove
        """
        if event in self._event_handlers:
            self._event_handlers[event] = [
                h for h in self._event_handlers[event] if h != handler
            ]

    async def _emit_event(self, event: str, data: Dict[str, Any]) -> None:
        """
        Emit an event to all registered handlers.

        Args:
            event: Event name
            data: Event data
        """
        if event not in self._event_handlers:
            return

        for handler in self._event_handlers[event]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, data)
                else:
                    handler(event, data)
            except Exception as e:
                logger.error(f"Error in event handler for '{event}': {e}")

    async def register_tool_manually(
        self,
        server_name: str,
        tool: ToolDefinition,
        overwrite: bool = False
    ) -> None:
        """
        Manually register a tool (useful for testing or manual setup).

        Args:
            server_name: Server name
            tool: Tool definition
            overwrite: Whether to overwrite existing tool
        """
        if server_name not in self._servers:
            raise ServerNotFoundError(f"Server not found: {server_name}")

        await self._registry.register_tool(server_name, tool, overwrite)
        self._servers[server_name].tool_count = await self._registry.get_tool_count(server_name)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"MCPBus(servers={len(self._servers)}, "
            f"tools={len(self._registry)}, "
            f"running={self._running})"
        )


# Singleton instance
_bus_instance: Optional[MCPBus] = None


def get_mcp_bus() -> MCPBus:
    """
    Get the singleton MCP Bus instance.

    Returns:
        MCPBus instance
    """
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = MCPBus()
    return _bus_instance


async def create_mcp_bus() -> MCPBus:
    """
    Create and start a new MCP Bus instance.

    Returns:
        Started MCPBus instance
    """
    bus = get_mcp_bus()
    await bus.start()
    return bus
