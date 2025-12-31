"""
Log Message Schemas

Pydantic schemas for real-time log streaming via WebSocket.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Log level enumeration"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LogMessage(BaseModel):
    """
    Log message from worker

    Sent by workers during subtask execution and broadcast to WebSocket clients.
    """
    subtask_id: UUID = Field(..., description="Subtask ID generating the log")
    task_id: UUID = Field(..., description="Parent task ID")
    level: LogLevel = Field(..., description="Log level")
    message: str = Field(..., description="Log message content")
    worker_id: Optional[UUID] = Field(None, description="Source worker ID")
    worker_name: Optional[str] = Field(None, description="Source worker machine name")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Log timestamp (UTC)")
    metadata: Optional[dict] = Field(None, description="Additional metadata (e.g., file, line number)")

    class Config:
        json_schema_extra = {
            "example": {
                "subtask_id": "550e8400-e29b-41d4-a716-446655440001",
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "level": "info",
                "message": "Processing request with Claude Code",
                "worker_id": "660e8400-e29b-41d4-a716-446655440002",
                "worker_name": "worker-node-01",
                "timestamp": "2025-12-08T10:30:00Z",
                "metadata": {"file": "main.py", "line": 42}
            }
        }


class LogRequest(BaseModel):
    """
    Request to create a log entry

    Sent by workers via POST /api/v1/subtasks/{subtask_id}/log
    """
    level: LogLevel = Field(..., description="Log level")
    message: str = Field(..., description="Log message content")
    metadata: Optional[dict] = Field(None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "level": "info",
                "message": "Starting code analysis",
                "metadata": {"module": "analyzer", "step": 1}
            }
        }


class LogResponse(BaseModel):
    """Response after creating a log entry"""
    success: bool = Field(..., description="Whether log was stored successfully")
    message: str = Field(..., description="Response message")
    broadcasted: int = Field(..., description="Number of WebSocket clients that received the log")


class WebSocketMessage(BaseModel):
    """
    WebSocket message envelope

    Wraps different message types sent over WebSocket connection.
    """
    type: str = Field(..., description="Message type: log | ping | pong | error | subscribed | unsubscribed")
    data: Optional[dict] = Field(None, description="Message payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp (UTC)")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "log",
                "data": {
                    "subtask_id": "550e8400-e29b-41d4-a716-446655440001",
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "level": "info",
                    "message": "Processing request",
                    "timestamp": "2025-12-08T10:30:00Z"
                },
                "timestamp": "2025-12-08T10:30:00Z"
            }
        }


class SubscribeRequest(BaseModel):
    """Request to subscribe to task logs"""
    action: str = Field(..., description="Action: subscribe | unsubscribe")
    task_id: UUID = Field(..., description="Task ID to subscribe to")

    class Config:
        json_schema_extra = {
            "example": {
                "action": "subscribe",
                "task_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
