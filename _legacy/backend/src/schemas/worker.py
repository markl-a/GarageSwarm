"""Worker-related Pydantic schemas"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class WorkerStatus(str, Enum):
    """Worker status enum"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"


class WorkerRegisterRequest(BaseModel):
    """Worker registration request"""
    machine_id: str = Field(..., description="Unique machine identifier (UUID)")
    machine_name: str = Field(..., min_length=1, max_length=100, description="Human-readable machine name")
    system_info: Dict[str, Any] = Field(..., description="System information (OS, CPU, memory, etc.)")
    tools: List[str] = Field(default_factory=list, description="Available AI tools (claude_code, gemini_cli, ollama)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "machine_id": "550e8400-e29b-41d4-a716-446655440000",
                "machine_name": "Development Machine",
                "system_info": {
                    "os": "Linux",
                    "os_version": "Ubuntu 22.04",
                    "cpu_count": 8,
                    "memory_total": 16000000000,
                    "python_version": "3.11.0"
                },
                "tools": ["claude_code", "gemini_cli"]
            }
        }
    )


class WorkerRegisterResponse(BaseModel):
    """Worker registration response"""
    status: str = Field(..., description="Registration status")
    worker_id: UUID = Field(..., description="Assigned worker ID")
    message: Optional[str] = Field(None, description="Additional message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "registered",
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "Worker registered successfully"
            }
        }
    )


class WorkerHeartbeatRequest(BaseModel):
    """Worker heartbeat request"""
    status: WorkerStatus = Field(..., description="Current worker status")
    resources: Dict[str, float] = Field(..., description="Current resource usage")
    current_task: Optional[UUID] = Field(None, description="Currently executing task ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "idle",
                "resources": {
                    "cpu_percent": 25.5,
                    "memory_percent": 60.2,
                    "disk_percent": 45.0
                },
                "current_task": None
            }
        }
    )


class WorkerHeartbeatResponse(BaseModel):
    """Worker heartbeat response"""
    acknowledged: bool = Field(..., description="Whether heartbeat was acknowledged")
    message: Optional[str] = Field(None, description="Additional message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "acknowledged": True,
                "message": "Heartbeat received"
            }
        }
    )


class WorkerSummary(BaseModel):
    """Worker summary for list view"""
    worker_id: UUID
    machine_name: str
    machine_id: str
    status: WorkerStatus
    tools: List[str]
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    last_heartbeat: Optional[datetime] = None
    registered_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkerListResponse(BaseModel):
    """Worker list response"""
    workers: List[WorkerSummary]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workers": [
                    {
                        "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                        "machine_name": "Development Machine",
                        "machine_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "online",
                        "tools": ["claude_code", "gemini_cli"],
                        "cpu_percent": 25.5,
                        "memory_percent": 60.2,
                        "disk_percent": 45.0,
                        "last_heartbeat": "2025-11-12T15:30:00Z",
                        "registered_at": "2025-11-12T10:00:00Z"
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0
            }
        }
    )


class WorkerDetailResponse(BaseModel):
    """Worker detail response"""
    worker_id: UUID
    machine_name: str
    machine_id: str
    status: WorkerStatus
    tools: List[str]
    system_info: Dict[str, Any]
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    current_task: Optional[UUID] = None
    last_heartbeat: Optional[datetime] = None
    registered_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "machine_name": "Development Machine",
                "machine_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "idle",
                "tools": ["claude_code", "gemini_cli"],
                "system_info": {
                    "os": "Linux",
                    "os_version": "Ubuntu 22.04",
                    "cpu_count": 8,
                    "memory_total": 16000000000
                },
                "cpu_percent": 25.5,
                "memory_percent": 60.2,
                "disk_percent": 45.0,
                "current_task": None,
                "last_heartbeat": "2025-11-12T15:30:00Z",
                "registered_at": "2025-11-12T10:00:00Z"
            }
        }
    )
