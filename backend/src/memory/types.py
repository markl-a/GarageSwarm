"""
Memory System Types

Data structures for the memory system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryEventType(str, Enum):
    """Types of memory events."""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    WORKER_REGISTERED = "worker_registered"
    WORKER_HEARTBEAT = "worker_heartbeat"
    TOOL_INVOKED = "tool_invoked"
    TOOL_RESULT = "tool_result"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    USER_FEEDBACK = "user_feedback"
    ERROR = "error"
    CUSTOM = "custom"


class MemoryEvent(BaseModel):
    """
    A memory event to be stored.

    Events capture significant actions or state changes in the system.
    """
    id: str = Field(default_factory=lambda: str(UUID))
    event_type: MemoryEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = ""  # Component that generated the event
    context: Dict[str, Any] = Field(default_factory=dict)

    # Related entities
    task_id: Optional[UUID] = None
    worker_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    user_id: Optional[UUID] = None

    # Event data
    data: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    # For learning
    success: Optional[bool] = None
    importance: float = 0.5  # 0-1 scale


class MemoryItem(BaseModel):
    """
    A retrievable memory item.

    Used as the result of memory queries.
    """
    id: str
    event_type: MemoryEventType
    timestamp: datetime
    source: str
    summary: str = ""
    relevance_score: float = 0.0
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskHistory(BaseModel):
    """History of a task's execution."""
    task_id: UUID
    events: List[MemoryEvent] = Field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: Optional[bool] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class WorkerStats(BaseModel):
    """Statistics for a worker's performance."""
    worker_id: UUID
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_execution_time_ms: float = 0.0
    last_active: Optional[datetime] = None
    tools_used: Dict[str, int] = Field(default_factory=dict)  # tool -> count

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks


class Feedback(BaseModel):
    """User feedback for a task or workflow."""
    task_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    success: bool
    rating: Optional[int] = None  # 1-5
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LearningPattern(BaseModel):
    """A learned pattern from successful or failed executions."""
    pattern_id: str
    pattern_type: str  # "success" or "failure"
    description: str
    context: Dict[str, Any] = Field(default_factory=dict)
    occurrences: int = 1
    confidence: float = 0.5
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
