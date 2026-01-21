"""
MCP Types and Data Structures

Core type definitions for the Model Context Protocol (MCP) implementation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPErrorCode(str, Enum):
    """MCP Error codes."""
    PARSE_ERROR = "parse_error"
    INVALID_REQUEST = "invalid_request"
    METHOD_NOT_FOUND = "method_not_found"
    INVALID_PARAMS = "invalid_params"
    INTERNAL_ERROR = "internal_error"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_EXECUTION_ERROR = "tool_execution_error"


class MCPMessageType(str, Enum):
    """MCP Message types."""
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    PING = "ping"
    SHUTDOWN = "shutdown"


class MCPServerStatus(str, Enum):
    """MCP Server connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class ToolResultStatus(str, Enum):
    """Tool execution result status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class MCPError(BaseModel):
    """MCP Error structure."""
    code: MCPErrorCode
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPMessage(BaseModel):
    """MCP JSON-RPC message structure."""
    id: str
    method: MCPMessageType
    params: Dict[str, Any] = Field(default_factory=dict)
    jsonrpc: str = "2.0"


class MCPResponse(BaseModel):
    """MCP JSON-RPC response structure."""
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[MCPError] = None
    jsonrpc: str = "2.0"


class MCPTransport(str, Enum):
    """MCP Transport types."""
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""
    name: str = ""
    transport: MCPTransport = MCPTransport.STDIO
    command: Optional[str] = None  # For STDIO transport
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None  # For SSE/WebSocket transport
    timeout: float = 60.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    capabilities: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """MCP Tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    server_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class ToolInvocation(BaseModel):
    """Record of a tool invocation."""
    id: str
    tool_path: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional["ToolResult"] = None


class ToolResult(BaseModel):
    """Result from a tool invocation."""
    tool_path: str
    status: ToolResultStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success(cls, tool_path: str, result: Any, execution_time: float = 0.0) -> "ToolResult":
        """Create a success result."""
        return cls(
            tool_path=tool_path,
            status=ToolResultStatus.SUCCESS,
            result=result,
            execution_time=execution_time
        )

    @classmethod
    def error(cls, tool_path: str, error: str, execution_time: float = 0.0) -> "ToolResult":
        """Create an error result."""
        return cls(
            tool_path=tool_path,
            status=ToolResultStatus.ERROR,
            error=error,
            execution_time=execution_time
        )


class ServerInfo(BaseModel):
    """Information about a registered MCP server."""
    name: str
    status: MCPServerStatus
    config: MCPServerConfig
    connected_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    tool_count: int = 0
    error_message: Optional[str] = None
    capabilities: Dict[str, Any] = Field(default_factory=dict)


# Forward reference update
ToolInvocation.model_rebuild()
