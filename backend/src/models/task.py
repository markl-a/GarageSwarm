"""
Task Model

Main task submissions from users, tracking overall progress and status
"""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, TEXT, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Task(Base):
    """Task model - main user-submitted tasks"""

    __tablename__ = "tasks"

    # Primary key
    task_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique task identifier",
    )

    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True,
        index=True,
        comment="Task owner (Future feature)",
    )

    # Task details
    description = Column(TEXT, nullable=False, comment="Natural language task description")

    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Task status: pending | initializing | in_progress | checkpoint | completed | failed | cancelled",
    )

    progress = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Overall progress percentage (0-100)",
    )

    # Configuration
    checkpoint_frequency = Column(
        String(20),
        nullable=False,
        default="medium",
        comment="Checkpoint frequency: low | medium | high",
    )

    privacy_level = Column(
        String(20),
        nullable=False,
        default="normal",
        comment="Privacy level: normal | sensitive",
    )

    tool_preferences = Column(
        JSONB,
        nullable=True,
        comment='Preferred AI tools: ["claude_code", "gemini_cli"]',
    )

    # Task metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    task_metadata = Column(JSONB, nullable=True, comment="Flexible metadata storage")

    # Optimistic locking
    version = Column(
        Integer, nullable=False, default=0, comment="Version for optimistic locking"
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
        TIMESTAMP(timezone=True), nullable=True, comment="Task execution start time"
    )

    completed_at = Column(
        TIMESTAMP(timezone=True), nullable=True, comment="Task completion time"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'initializing', 'in_progress', 'checkpoint', 'completed', 'failed', 'cancelled')",
            name="chk_task_status",
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100", name="chk_task_progress"
        ),
        CheckConstraint(
            "checkpoint_frequency IN ('low', 'medium', 'high')",
            name="chk_checkpoint_frequency",
        ),
        CheckConstraint(
            "privacy_level IN ('normal', 'sensitive')", name="chk_privacy_level"
        ),
    )

    # Relationships
    user = relationship("User", back_populates="tasks")
    subtasks = relationship(
        "Subtask", back_populates="task", cascade="all, delete-orphan"
    )
    checkpoints = relationship(
        "Checkpoint", back_populates="task", cascade="all, delete-orphan"
    )
    activity_logs = relationship(
        "ActivityLog", back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Task(task_id={self.task_id}, status={self.status}, progress={self.progress}%)>"

    def is_pending(self) -> bool:
        """Check if task is pending"""
        return self.status == "pending"

    def is_in_progress(self) -> bool:
        """Check if task is in progress"""
        return self.status == "in_progress"

    def is_completed(self) -> bool:
        """Check if task is completed"""
        return self.status == "completed"

    def is_failed(self) -> bool:
        """Check if task failed"""
        return self.status == "failed"

    def requires_checkpoint(self) -> bool:
        """Check if task is at a checkpoint"""
        return self.status == "checkpoint"
