"""
Task Model

Main task submissions from users, tracking overall progress and status.
"""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, TEXT, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Task(Base):
    """Task model - main user-submitted tasks."""

    __tablename__ = "tasks"

    task_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique task identifier",
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Task owner",
    )

    worker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workers.worker_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Assigned worker",
    )

    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.workflow_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parent workflow (if part of workflow)",
    )

    node_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Workflow node this task belongs to",
    )

    description = Column(
        TEXT,
        nullable=False,
        comment="Natural language task description",
    )

    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Task status",
    )

    progress = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Overall progress percentage (0-100)",
    )

    # Configuration
    tool_preference = Column(
        String(50),
        nullable=True,
        comment="Preferred AI tool for execution",
    )

    priority = Column(
        Integer,
        default=5,
        nullable=False,
        comment="Task priority (1-10, higher = more urgent)",
    )

    task_metadata = Column(
        JSONB,
        nullable=True,
        comment="Flexible metadata storage",
    )

    result = Column(
        JSONB,
        nullable=True,
        comment="Task execution result",
    )

    error = Column(
        TEXT,
        nullable=True,
        comment="Error message if failed",
    )

    # Optimistic locking
    version = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Version for optimistic locking",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Task creation time",
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update time",
    )

    started_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Task execution start time",
    )

    completed_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Task completion time",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'queued', 'assigned', 'running', 'completed', 'failed', 'cancelled')",
            name="chk_task_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="chk_task_progress"),
        CheckConstraint("priority >= 1 AND priority <= 10", name="chk_task_priority"),
    )

    # Relationships
    user = relationship("User", back_populates="tasks")
    worker = relationship("Worker", back_populates="tasks")
    workflow = relationship("Workflow", back_populates="tasks")

    def __repr__(self):
        return f"<Task(task_id={self.task_id}, status={self.status}, progress={self.progress}%)>"

    def is_pending(self) -> bool:
        return self.status == "pending"

    def is_running(self) -> bool:
        return self.status == "running"

    def is_completed(self) -> bool:
        return self.status == "completed"

    def is_failed(self) -> bool:
        return self.status == "failed"
