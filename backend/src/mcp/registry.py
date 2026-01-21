"""
MCP Tool Registry

Manages tool definitions and provides search/lookup functionality.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional

from .types import ToolDefinition


logger = logging.getLogger(__name__)


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not found."""
    pass


class ToolAlreadyExistsError(Exception):
    """Raised when trying to register a tool that already exists."""
    pass


class ToolRegistry:
    """
    Registry for managing MCP tool definitions.

    Provides methods to register, retrieve, list, and search tools
    from multiple MCP servers.
    """

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, ToolDefinition] = {}
        self._server_tools: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
        logger.info("ToolRegistry initialized")

    async def register_tool(
        self,
        server_name: str,
        tool: ToolDefinition,
        overwrite: bool = False
    ) -> None:
        """
        Register a tool from an MCP server.

        Args:
            server_name: Name of the server providing the tool
            tool: Tool definition to register
            overwrite: If True, overwrite existing tool; otherwise raise error

        Raises:
            ToolAlreadyExistsError: If tool exists and overwrite is False
        """
        tool_path = f"{server_name}.{tool.name}"

        async with self._lock:
            if tool_path in self._tools and not overwrite:
                raise ToolAlreadyExistsError(
                    f"Tool '{tool_path}' already exists. Use overwrite=True to replace."
                )

            # Ensure tool has correct server_name
            tool_data = tool.model_dump()
            tool_data["server_name"] = server_name
            registered_tool = ToolDefinition(**tool_data)

            self._tools[tool_path] = registered_tool

            # Track tools by server
            if server_name not in self._server_tools:
                self._server_tools[server_name] = []
            if tool_path not in self._server_tools[server_name]:
                self._server_tools[server_name].append(tool_path)

            logger.info(f"Registered tool: {tool_path}")

    async def register_tools(
        self,
        server_name: str,
        tools: List[ToolDefinition],
        overwrite: bool = False
    ) -> int:
        """
        Register multiple tools from an MCP server.

        Args:
            server_name: Name of the server providing the tools
            tools: List of tool definitions to register
            overwrite: If True, overwrite existing tools

        Returns:
            Number of tools registered
        """
        count = 0
        for tool in tools:
            try:
                await self.register_tool(server_name, tool, overwrite)
                count += 1
            except ToolAlreadyExistsError:
                logger.warning(
                    f"Tool '{server_name}.{tool.name}' already exists, skipping"
                )
        return count

    async def unregister_tool(self, tool_path: str) -> bool:
        """
        Unregister a tool.

        Args:
            tool_path: Full tool path (server.tool_name)

        Returns:
            True if tool was unregistered, False if not found
        """
        async with self._lock:
            if tool_path not in self._tools:
                return False

            tool = self._tools.pop(tool_path)

            # Remove from server tracking
            if tool.server_name in self._server_tools:
                if tool_path in self._server_tools[tool.server_name]:
                    self._server_tools[tool.server_name].remove(tool_path)
                if not self._server_tools[tool.server_name]:
                    del self._server_tools[tool.server_name]

            logger.info(f"Unregistered tool: {tool_path}")
            return True

    async def unregister_server_tools(self, server_name: str) -> int:
        """
        Unregister all tools from a server.

        Args:
            server_name: Name of the server

        Returns:
            Number of tools unregistered
        """
        async with self._lock:
            if server_name not in self._server_tools:
                return 0

            tool_paths = self._server_tools.pop(server_name)
            count = 0

            for tool_path in tool_paths:
                if tool_path in self._tools:
                    del self._tools[tool_path]
                    count += 1

            logger.info(f"Unregistered {count} tools from server: {server_name}")
            return count

    async def get_tool(self, tool_path: str) -> ToolDefinition:
        """
        Get a tool definition by path.

        Args:
            tool_path: Full tool path (server.tool_name)

        Returns:
            Tool definition

        Raises:
            ToolNotFoundError: If tool is not found
        """
        if tool_path not in self._tools:
            raise ToolNotFoundError(f"Tool not found: {tool_path}")
        return self._tools[tool_path]

    async def get_tool_safe(self, tool_path: str) -> Optional[ToolDefinition]:
        """
        Get a tool definition by path, returning None if not found.

        Args:
            tool_path: Full tool path (server.tool_name)

        Returns:
            Tool definition or None
        """
        return self._tools.get(tool_path)

    async def list_tools(
        self,
        server_name: Optional[str] = None
    ) -> List[ToolDefinition]:
        """
        List all registered tools or tools from a specific server.

        Args:
            server_name: Optional server name to filter by

        Returns:
            List of tool definitions
        """
        if server_name is not None:
            tool_paths = self._server_tools.get(server_name, [])
            return [self._tools[path] for path in tool_paths if path in self._tools]

        return list(self._tools.values())

    async def list_tool_paths(
        self,
        server_name: Optional[str] = None
    ) -> List[str]:
        """
        List all registered tool paths or paths from a specific server.

        Args:
            server_name: Optional server name to filter by

        Returns:
            List of tool paths
        """
        if server_name is not None:
            return list(self._server_tools.get(server_name, []))

        return list(self._tools.keys())

    async def search_tools(
        self,
        query: str,
        server_name: Optional[str] = None,
        case_sensitive: bool = False
    ) -> List[ToolDefinition]:
        """
        Search tools by name or description.

        Args:
            query: Search query (supports regex)
            server_name: Optional server name to filter by
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of matching tool definitions
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error:
            # If query is not valid regex, escape it
            pattern = re.compile(re.escape(query), flags)

        tools = await self.list_tools(server_name)
        results = []

        for tool in tools:
            # Search in name and description
            if pattern.search(tool.name) or pattern.search(tool.description):
                results.append(tool)

        return results

    async def get_servers(self) -> List[str]:
        """
        Get list of servers with registered tools.

        Returns:
            List of server names
        """
        return list(self._server_tools.keys())

    async def get_tool_count(self, server_name: Optional[str] = None) -> int:
        """
        Get the number of registered tools.

        Args:
            server_name: Optional server name to count tools for

        Returns:
            Number of tools
        """
        if server_name is not None:
            return len(self._server_tools.get(server_name, []))
        return len(self._tools)

    async def has_tool(self, tool_path: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            tool_path: Full tool path (server.tool_name)

        Returns:
            True if tool exists
        """
        return tool_path in self._tools

    async def clear(self) -> int:
        """
        Clear all registered tools.

        Returns:
            Number of tools cleared
        """
        async with self._lock:
            count = len(self._tools)
            self._tools.clear()
            self._server_tools.clear()
            logger.info(f"Cleared {count} tools from registry")
            return count

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __contains__(self, tool_path: str) -> bool:
        """Check if a tool path is registered."""
        return tool_path in self._tools
