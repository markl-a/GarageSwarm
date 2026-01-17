"""
Subtask Model

Decomposed subtasks from main tasks, forming a DAG (Directed Acyclic Graph)
"""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, TEXT, TIMESTAMP, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Subtask(Base):
    """Subtask model - decomposed subtasks forming a DAG"""

    __tablename__ = "subtasks"

    # Primary key
    subtask_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique subtask identifier",
    )

    # Foreign key to task
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent task ID",
    )

    # Subtask details
    name = Column(String(255), nullable=False, comment="Short subtask name")

    description = Column(TEXT, nullable=False, comment="Detailed subtask description")

    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Subtask status: pending | queued | in_progress | completed | failed | correcting",
    )

    progress = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Subtask progress percentage (0-100)",
    )

    # Dependencies (DAG)
    dependencies = Column(
        JSONB,
        default=[],
        server_default=text("'[]'::jsonb"),
        comment="Dependency subtask IDs: [uuid1, uuid2]",
    )

    # Subtask type for workflow management
    subtask_type = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Subtask type: code_generation | code_review | code_fix | test | documentation | analysis | deployment",
    )

    # Tool assignment
    recommended_tool = Column(
        String(50),
        nullable=True,
        comment="Recommended AI tool: claude_code | gemini_cli | ollama",
    )

    assigned_worker = Column(
        UUID(as_uuid=True),
        ForeignKey("workers.worker_id"),
        nullable=True,
        index=True,
        comment="Assigned worker ID",
    )

    assigned_tool = Column(
        String(50), nullable=True, comment="Actually assigned AI tool"
    )

    # Complexity & Priority
    complexity = Column(
        Integer,
        nullable=True,
        comment="Complexity rating: 1 (simple) to 5 (complex)",
    )

    priority = Column(Integer, default=0, nullable=False, comment="Priority score (higher = more urgent)")

    # Output
    output = Column(
        JSONB,
        nullable=True,
        comment="Execution output: {text: '...', files: [...], usage: {...}}",
    )

    error = Column(TEXT, nullable=True, comment="Error message if failed")

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Subtask creation time",
    )

    started_at = Column(
        TIMESTAMP(timezone=True), nullable=True, comment="Execution start time"
    )

    completed_at = Column(
        TIMESTAMP(timezone=True), nullable=True, comment="Completion time"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'queued', 'in_progress', 'completed', 'failed', 'correcting')",
            name="chk_subtask_status",
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100", name="chk_subtask_progress"
        ),
        CheckConstraint(
            "complexity >= 1 AND complexity <= 5", name="chk_subtask_complexity"
        ),
        CheckConstraint(
            "subtask_type IS NULL OR subtask_type IN ('code_generation', 'code_review', 'code_fix', 'test', 'documentation', 'analysis', 'deployment')",
            name="chk_subtask_type",
        ),
    )

    # Relationships
    task = relationship("Task", back_populates="subtasks")
    worker = relationship("Worker", back_populates="subtasks")
    evaluations = relationship(
        "Evaluation", back_populates="subtask", cascade="all, delete-orphan"
    )
    corrections = relationship("Correction", back_populates="subtask")
    activity_logs = relationship(
        "ActivityLog", back_populates="subtask", cascade="all, delete-orphan"
    )
    proposals = relationship(
        "Proposal", back_populates="subtask", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Subtask(subtask_id={self.subtask_id}, name={self.name}, status={self.status})>"

    def is_pending(self) -> bool:
        """Check if subtask is pending"""
        return self.status == "pending"

    def is_queued(self) -> bool:
        """Check if subtask is queued"""
        return self.status == "queued"

    def is_in_progress(self) -> bool:
        """Check if subtask is in progress"""
        return self.status == "in_progress"

    def is_completed(self) -> bool:
        """Check if subtask is completed"""
        return self.status == "completed"

    def is_failed(self) -> bool:
        """Check if subtask failed"""
        return self.status == "failed"

    def has_dependencies(self) -> bool:
        """Check if subtask has dependencies"""
        return bool(self.dependencies) and len(self.dependencies) > 0

    def is_assigned(self) -> bool:
        """Check if subtask is assigned to a worker"""
        return self.assigned_worker is not None
