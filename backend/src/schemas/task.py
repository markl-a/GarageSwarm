"""Task-related Pydantic schemas"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    """Task status enum"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    IN_PROGRESS = "in_progress"
    CHECKPOINT = "checkpoint"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Task type enum"""
    DEVELOP_FEATURE = "develop_feature"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


class CheckpointFrequency(str, Enum):
    """Checkpoint frequency enum"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PrivacyLevel(str, Enum):
    """Privacy level enum"""
    NORMAL = "normal"
    SENSITIVE = "sensitive"


class TaskCreateRequest(BaseModel):
    """Task creation request"""
    description: str = Field(..., min_length=10, max_length=10000, description="Task description (supports Markdown)")
    task_type: TaskType = Field(default=TaskType.DEVELOP_FEATURE, description="Type of task")
    requirements: Optional[Dict[str, Any]] = Field(default=None, description="Additional requirements")
    checkpoint_frequency: CheckpointFrequency = Field(default=CheckpointFrequency.MEDIUM, description="How often to create checkpoints")
    privacy_level: PrivacyLevel = Field(default=PrivacyLevel.NORMAL, description="Privacy level for the task")
    tool_preferences: Optional[List[str]] = Field(default=None, description="Preferred AI tools")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Create a Python function that calculates fibonacci numbers with memoization",
                "task_type": "develop_feature",
                "requirements": {
                    "language": "python",
                    "include_tests": True
                },
                "checkpoint_frequency": "medium",
                "privacy_level": "normal",
                "tool_preferences": ["claude_code"]
            }
        }
    )


class TaskCreateResponse(BaseModel):
    """Task creation response"""
    task_id: UUID = Field(..., description="Created task ID")
    status: TaskStatus = Field(..., description="Initial task status")
    message: str = Field(..., description="Response message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pending",
                "message": "Task created successfully"
            }
        }
    )


class EvaluationScores(BaseModel):
    """Evaluation scores for a subtask"""
    overall_score: Optional[float] = Field(None, ge=0, le=10, description="Overall evaluation score (0-10)")
    code_quality: Optional[float] = Field(None, ge=0, le=10)
    completeness: Optional[float] = Field(None, ge=0, le=10)
    security: Optional[float] = Field(None, ge=0, le=10)
    architecture: Optional[float] = Field(None, ge=0, le=10)
    testability: Optional[float] = Field(None, ge=0, le=10)

    model_config = ConfigDict(from_attributes=True)


class SubtaskSummary(BaseModel):
    """Subtask summary for task detail view"""
    subtask_id: UUID
    name: str
    status: str
    progress: int = Field(ge=0, le=100)
    assigned_worker: Optional[UUID] = None
    assigned_tool: Optional[str] = None
    evaluation: Optional[EvaluationScores] = Field(None, description="Evaluation scores if available")

    model_config = ConfigDict(from_attributes=True)


class TaskDetailResponse(BaseModel):
    """Task detail response"""
    task_id: UUID
    description: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    checkpoint_frequency: CheckpointFrequency
    privacy_level: PrivacyLevel
    tool_preferences: Optional[List[str]] = None
    task_metadata: Optional[Dict[str, Any]] = None
    subtasks: List[SubtaskSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Create a Python function...",
                "status": "in_progress",
                "progress": 45,
                "checkpoint_frequency": "medium",
                "privacy_level": "normal",
                "tool_preferences": ["claude_code"],
                "subtasks": [
                    {
                        "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                        "name": "Generate code",
                        "status": "completed",
                        "progress": 100,
                        "assigned_worker": "789e0123-e89b-12d3-a456-426614174002",
                        "assigned_tool": "claude_code"
                    }
                ],
                "created_at": "2025-11-12T10:00:00Z",
                "updated_at": "2025-11-12T10:30:00Z",
                "started_at": "2025-11-12T10:05:00Z",
                "completed_at": None
            }
        }
    )


class TaskSummary(BaseModel):
    """Task summary for list view"""
    task_id: UUID
    description: str = Field(max_length=200)
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Task list response with pagination"""
    tasks: List[TaskSummary]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tasks": [
                    {
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "description": "Create a Python function...",
                        "status": "in_progress",
                        "progress": 45,
                        "created_at": "2025-11-12T10:00:00Z",
                        "updated_at": "2025-11-12T10:30:00Z"
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0
            }
        }
    )


class TaskCancelResponse(BaseModel):
    """Task cancel response"""
    task_id: UUID
    status: TaskStatus
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "cancelled",
                "message": "Task cancelled successfully"
            }
        }
    )


class TaskProgressResponse(BaseModel):
    """Task progress response from Redis cache"""
    task_id: str = Field(..., description="Task UUID as string")
    status: Optional[str] = Field(None, description="Current task status")
    progress: Optional[int] = Field(None, description="Current progress percentage (0-100)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "in_progress",
                "progress": 45
            }
        }
    )


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskPriorityUpdateRequest(BaseModel):
    """Update task priority request"""
    priority: TaskPriority = Field(..., description="New priority level")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "priority": "high"
            }
        }
    )


class BatchTaskRequest(BaseModel):
    """Batch operation request for multiple tasks"""
    task_ids: List[UUID] = Field(..., min_length=1, max_length=100, description="List of task IDs")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_ids": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "456e7890-e89b-12d3-a456-426614174001"
                ]
            }
        }
    )


class BatchOperationResult(BaseModel):
    """Result of batch operation on a single task"""
    task_id: UUID
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BatchOperationResponse(BaseModel):
    """Batch operation response"""
    operation: str = Field(..., description="Operation performed")
    total: int = Field(..., description="Total tasks in request")
    successful: int = Field(..., description="Successfully processed tasks")
    failed: int = Field(..., description="Failed tasks")
    results: List[BatchOperationResult] = Field(..., description="Individual results")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "operation": "cancel",
                "total": 2,
                "successful": 2,
                "failed": 0,
                "results": [
                    {"task_id": "123e4567-e89b-12d3-a456-426614174000", "success": True, "message": "Cancelled"},
                    {"task_id": "456e7890-e89b-12d3-a456-426614174001", "success": True, "message": "Cancelled"}
                ]
            }
        }
    )


class TaskAnalytics(BaseModel):
    """Task analytics data"""
    total_tasks: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    average_completion_time_hours: Optional[float] = None
    completion_rate: float = Field(..., ge=0, le=100, description="Percentage of completed tasks")
    failure_rate: float = Field(..., ge=0, le=100, description="Percentage of failed tasks")
    active_tasks: int
    pending_tasks: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_tasks": 100,
                "by_status": {"completed": 60, "in_progress": 25, "pending": 10, "failed": 5},
                "by_priority": {"normal": 50, "high": 30, "urgent": 15, "low": 5},
                "average_completion_time_hours": 2.5,
                "completion_rate": 60.0,
                "failure_rate": 5.0,
                "active_tasks": 25,
                "pending_tasks": 10
            }
        }
    )


class WorkerAnalytics(BaseModel):
    """Worker analytics data"""
    total_workers: int
    by_status: Dict[str, int]
    online_workers: int
    busy_workers: int
    idle_workers: int
    average_tasks_per_worker: float
    top_performers: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SystemAnalytics(BaseModel):
    """System-wide analytics"""
    timestamp: datetime
    tasks: TaskAnalytics
    workers: WorkerAnalytics
    subtasks: Dict[str, int] = Field(..., description="Subtask counts by status")
    queue_length: int
    throughput_per_hour: float = Field(..., description="Tasks completed per hour (last 24h)")

    model_config = ConfigDict(from_attributes=True)
