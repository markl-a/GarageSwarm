"""
Task Schemas

Request and response models for task endpoints.
"""

from datetime import datetime
from typing import Optional, Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """Task creation request."""

    description: str = Field(..., min_length=1, max_length=10000)
    tool_preference: Optional[str] = Field(None, max_length=50)
    priority: int = Field(default=5, ge=1, le=10)
    workflow_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskUpdate(BaseModel):
    """Task update request."""

    description: Optional[str] = Field(None, min_length=1, max_length=10000)
    status: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    priority: Optional[int] = Field(None, ge=1, le=10)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TaskResponse(BaseModel):
    """Task response."""

    task_id: UUID
    user_id: Optional[UUID] = None
    worker_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    description: str
    status: str
    progress: int
    priority: int
    tool_preference: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Paginated task list response."""

    tasks: List[TaskResponse]
    total: int
    limit: int
    offset: int
