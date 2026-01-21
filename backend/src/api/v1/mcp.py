"""
MCP API Endpoints

Provides REST API endpoints for managing MCP servers and invoking tools.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.mcp import (
    get_mcp_bus,
    MCPServerConfig,
    MCPTransport,
    ToolDefinition,
    ServerInfo,
)
from src.mcp.bus import ServerNotFoundError, ToolInvocationError
from src.mcp.registry import ToolNotFoundError

router = APIRouter()


# ==================== Request/Response Schemas ====================


class ServerRegisterRequest(BaseModel):
    """Request to register an MCP server."""
    name: str = Field(..., description="Unique name for the server")
    transport: str = Field(default="stdio", description="Transport type (stdio, sse)")
    command: Optional[str] = Field(None, description="Command to run (for STDIO)")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    url: Optional[str] = Field(None, description="Server URL (for SSE)")
    timeout: float = Field(default=60.0, description="Timeout in seconds")


class ToolInvokeRequest(BaseModel):
    """Request to invoke an MCP tool."""
    tool_path: str = Field(..., description="Full tool path (server.tool_name)")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    timeout: Optional[float] = Field(None, description="Optional timeout override")


class ToolInvokeResponse(BaseModel):
    """Response from tool invocation."""
    status: str
    tool_path: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float


class ServerStatusResponse(BaseModel):
    """Server status response."""
    name: str
    status: str
    connected: bool
    tool_count: int
    connected_at: Optional[str] = None
    error: Optional[str] = None


class BusHealthResponse(BaseModel):
    """MCP Bus health response."""
    bus_running: bool
    total_servers: int
    connected_servers: int
    total_tools: int
    servers: Dict[str, Any]


# ==================== API Endpoints ====================


@router.get("/health", response_model=BusHealthResponse)
async def get_mcp_health():
    """Get MCP Bus health status."""
    bus = get_mcp_bus()
    health = await bus.health_check()
    return health


@router.get("/servers", response_model=List[ServerStatusResponse])
async def list_servers():
    """List all registered MCP servers."""
    bus = get_mcp_bus()
    servers = await bus.get_all_servers()

    return [
        ServerStatusResponse(
            name=s.name,
            status=s.status,
            connected=s.status == "connected",
            tool_count=s.tool_count,
            connected_at=s.connected_at.isoformat() if s.connected_at else None,
            error=s.error_message
        )
        for s in servers
    ]


@router.post("/servers", response_model=ServerStatusResponse, status_code=status.HTTP_201_CREATED)
async def register_server(request: ServerRegisterRequest):
    """Register a new MCP server."""
    bus = get_mcp_bus()

    try:
        transport = MCPTransport(request.transport)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transport type: {request.transport}. Valid: stdio, sse, websocket"
        )

    config = MCPServerConfig(
        name=request.name,
        transport=transport,
        command=request.command,
        args=request.args,
        env=request.env,
        url=request.url,
        timeout=request.timeout
    )

    try:
        server_info = await bus.register_server(request.name, config)
        return ServerStatusResponse(
            name=server_info.name,
            status=server_info.status,
            connected=server_info.status == "connected",
            tool_count=server_info.tool_count,
            connected_at=server_info.connected_at.isoformat() if server_info.connected_at else None,
            error=server_info.error_message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/servers/{server_name}", response_model=ServerStatusResponse)
async def get_server(server_name: str):
    """Get status of a specific MCP server."""
    bus = get_mcp_bus()

    try:
        server_info = await bus.get_server_status(server_name)
        return ServerStatusResponse(
            name=server_info.name,
            status=server_info.status,
            connected=server_info.status == "connected",
            tool_count=server_info.tool_count,
            connected_at=server_info.connected_at.isoformat() if server_info.connected_at else None,
            error=server_info.error_message
        )
    except ServerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}"
        )


@router.delete("/servers/{server_name}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_server(server_name: str):
    """Unregister an MCP server."""
    bus = get_mcp_bus()

    try:
        await bus.unregister_server(server_name)
    except ServerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}"
        )


@router.post("/servers/{server_name}/reconnect", response_model=ServerStatusResponse)
async def reconnect_server(server_name: str):
    """Reconnect to an MCP server."""
    bus = get_mcp_bus()

    try:
        await bus.reconnect_server(server_name)
        server_info = await bus.get_server_status(server_name)
        return ServerStatusResponse(
            name=server_info.name,
            status=server_info.status,
            connected=server_info.status == "connected",
            tool_count=server_info.tool_count,
            connected_at=server_info.connected_at.isoformat() if server_info.connected_at else None,
            error=server_info.error_message
        )
    except ServerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}"
        )


@router.get("/tools")
async def list_tools(server_name: Optional[str] = None):
    """List all available MCP tools."""
    bus = get_mcp_bus()
    tools = await bus.get_available_tools(server_name)

    return {
        "total": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "server": t.server_name,
                "input_schema": t.input_schema
            }
            for t in tools
        ]
    }


@router.get("/tools/{tool_path:path}")
async def get_tool(tool_path: str):
    """Get details of a specific MCP tool."""
    bus = get_mcp_bus()

    try:
        tool = await bus.registry.get_tool(tool_path)
        return {
            "name": tool.name,
            "description": tool.description,
            "server": tool.server_name,
            "input_schema": tool.input_schema
        }
    except ToolNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_path}"
        )


@router.post("/tools/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(request: ToolInvokeRequest):
    """Invoke an MCP tool."""
    bus = get_mcp_bus()

    try:
        result = await bus.invoke_tool(
            request.tool_path,
            request.arguments,
            request.timeout
        )

        return ToolInvokeResponse(
            status=result.status,
            tool_path=result.tool_path,
            result=result.result,
            error=result.error,
            execution_time=result.execution_time
        )
    except ToolNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {request.tool_path}"
        )
    except ServerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ToolInvocationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/servers/{server_name}/tools")
async def register_tool(server_name: str, tool: Dict[str, Any]):
    """Manually register a tool for a server."""
    bus = get_mcp_bus()

    try:
        tool_def = ToolDefinition(
            name=tool.get("name", ""),
            description=tool.get("description", ""),
            input_schema=tool.get("input_schema", {}),
            server_name=server_name
        )
        await bus.register_tool_manually(server_name, tool_def)
        return {"status": "registered", "tool": tool_def.name}
    except ServerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
