"""Subtask-related Pydantic schemas"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class SubtaskStatus(str, Enum):
    """Subtask status enum"""
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRECTING = "correcting"


class SubtaskCreateRequest(BaseModel):
    """Manual subtask creation request"""
    name: str = Field(..., min_length=1, max_length=255, description="Subtask name")
    description: str = Field(..., min_length=1, description="Subtask description")
    recommended_tool: Optional[str] = Field(None, description="Recommended AI tool")
    complexity: Optional[int] = Field(None, ge=1, le=5, description="Complexity rating (1-5)")
    priority: int = Field(default=50, ge=0, le=100, description="Priority score")
    dependencies: List[UUID] = Field(default_factory=list, description="Dependency subtask IDs")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Code Generation",
                "description": "Generate the main implementation",
                "recommended_tool": "claude_code",
                "complexity": 3,
                "priority": 100,
                "dependencies": []
            }
        }
    )


class SubtaskResponse(BaseModel):
    """Subtask detail response"""
    subtask_id: UUID
    task_id: UUID
    name: str
    description: str
    status: SubtaskStatus
    progress: int = Field(ge=0, le=100)
    recommended_tool: Optional[str] = None
    assigned_worker: Optional[UUID] = None
    assigned_tool: Optional[str] = None
    complexity: Optional[int] = None
    priority: int = 0
    dependencies: List[str] = Field(default_factory=list)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Code Generation",
                "description": "Generate the main implementation",
                "status": "pending",
                "progress": 0,
                "recommended_tool": "claude_code",
                "complexity": 3,
                "priority": 100,
                "dependencies": [],
                "created_at": "2025-11-12T10:00:00Z"
            }
        }
    )


class SubtaskListResponse(BaseModel):
    """Subtask list response"""
    subtasks: List[SubtaskResponse]
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subtasks": [
                    {
                        "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Code Generation",
                        "status": "pending",
                        "progress": 0
                    }
                ],
                "total": 1
            }
        }
    )


class TaskDecomposeRequest(BaseModel):
    """Request to decompose a task into subtasks"""
    task_type_override: Optional[str] = Field(
        None,
        description="Override task type for decomposition"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_type_override": "develop_feature"
            }
        }
    )


class TaskDecomposeResponse(BaseModel):
    """Response after task decomposition"""
    task_id: UUID
    subtask_count: int
    subtasks: List[SubtaskResponse]
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "subtask_count": 4,
                "subtasks": [],
                "message": "Task decomposed into 4 subtasks"
            }
        }
    )


class ReadySubtasksResponse(BaseModel):
    """Response with subtasks ready for execution"""
    task_id: UUID
    ready_subtasks: List[SubtaskResponse]
    total_ready: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "ready_subtasks": [],
                "total_ready": 2
            }
        }
    )


class SubtaskResultRequest(BaseModel):
    """Request to upload subtask execution result"""
    status: SubtaskStatus = Field(
        ...,
        description="Execution status: 'completed' or 'failed'"
    )
    result: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution result data"
    )
    execution_time: float = Field(
        ...,
        ge=0,
        description="Execution time in seconds"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if failed"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "completed",
                "result": {
                    "output": "Task completed successfully",
                    "files_created": ["main.py", "test.py"],
                    "tokens_used": 1500
                },
                "execution_time": 45.3,
                "error": None
            }
        }
    )


class SubtaskResultResponse(BaseModel):
    """Response after uploading subtask result"""
    subtask_id: UUID
    status: SubtaskStatus
    progress: int
    message: str
    newly_allocated: int = Field(
        0,
        description="Number of newly allocated subtasks"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                "status": "completed",
                "progress": 100,
                "message": "Subtask result uploaded successfully",
                "newly_allocated": 2
            }
        }
    )
