"""
Worker Schemas

Request and response models for worker endpoints.
"""

from datetime import datetime
from typing import Optional, Any, Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class WorkerRegister(BaseModel):
    """Worker registration request."""

    machine_id: str = Field(..., min_length=1, max_length=100)
    machine_name: str = Field(..., min_length=1, max_length=100)
    tools: List[str] = Field(default_factory=list)
    system_info: Optional[Dict[str, Any]] = None


class WorkerHeartbeat(BaseModel):
    """Worker heartbeat request."""

    status: str = Field(..., pattern=r"^(online|offline|busy|idle)$")
    cpu_percent: Optional[float] = Field(None, ge=0, le=100)
    memory_percent: Optional[float] = Field(None, ge=0, le=100)
    disk_percent: Optional[float] = Field(None, ge=0, le=100)
    tools: Optional[List[str]] = None
    current_task_id: Optional[UUID] = None


class WorkerResponse(BaseModel):
    """Worker response."""

    worker_id: UUID
    machine_id: str
    machine_name: str
    status: str
    tools: List[str]
    system_info: Optional[Dict[str, Any]] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    last_heartbeat: Optional[datetime] = None
    registered_at: datetime

    model_config = {"from_attributes": True}


class WorkerListResponse(BaseModel):
    """Paginated worker list response."""

    workers: List[WorkerResponse]
    total: int
    limit: int
    offset: int


class WorkerTaskAssignment(BaseModel):
    """Task assignment pushed to worker."""

    task_id: UUID
    description: str
    tool_preference: Optional[str] = None
    priority: int
    workflow_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskCompleteRequest(BaseModel):
    """Task completion request from worker."""

    task_id: UUID
    result: Dict[str, Any] = Field(default_factory=dict)


class TaskFailedRequest(BaseModel):
    """Task failure request from worker."""

    task_id: UUID
    error: str


class TaskResultReport(BaseModel):
    """Task result report from worker - unified completion/failure reporting."""

    task_id: UUID
    status: Literal["completed", "failed", "cancelled"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int = Field(..., ge=0, description="Execution time in milliseconds")
    metrics: Optional[Dict[str, int]] = Field(
        None, description="Execution metrics (e.g., tokens_used, api_calls)"
    )


class TaskResultResponse(BaseModel):
    """Response for task result reporting."""

    status: str = "success"
    task_id: UUID
    task_status: str
    message: str
