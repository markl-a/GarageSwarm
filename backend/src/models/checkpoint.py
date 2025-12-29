"""
Checkpoint Model

Quality checkpoints for human review and decision-making
"""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKey, String, TEXT, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Checkpoint(Base):
    """Checkpoint model - quality checkpoints for human review"""

    __tablename__ = "checkpoints"

    # Primary key
    checkpoint_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique checkpoint identifier",
    )

    # Foreign key to task
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Related task ID",
    )

    # Checkpoint details
    status = Column(
        String(20),
        nullable=False,
        default="pending_review",
        index=True,
        comment="Checkpoint status: pending_review | approved | corrected | rejected",
    )

    subtasks_completed = Column(
        JSONB,
        nullable=False,
        comment="Completed subtask IDs at this checkpoint: [uuid1, uuid2]",
    )

    # User decision
    user_decision = Column(
        String(20),
        nullable=True,
        comment="User decision: approve | correct | reject",
    )

    decision_notes = Column(TEXT, nullable=True, comment="User's notes/feedback")

    # Timestamps
    triggered_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Checkpoint trigger time",
    )

    reviewed_at = Column(
        TIMESTAMP(timezone=True), nullable=True, comment="User review time"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review', 'approved', 'corrected', 'rejected')",
            name="chk_checkpoint_status",
        ),
        CheckConstraint(
            "user_decision IS NULL OR user_decision IN ('approve', 'correct', 'reject')",
            name="chk_user_decision",
        ),
    )

    # Relationships
    task = relationship("Task", back_populates="checkpoints")
    corrections = relationship(
        "Correction", back_populates="checkpoint", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Checkpoint(checkpoint_id={self.checkpoint_id}, status={self.status})>"

    def is_pending(self) -> bool:
        """Check if checkpoint is pending review"""
        return self.status == "pending_review"

    def is_approved(self) -> bool:
        """Check if checkpoint was approved"""
        return self.status == "approved"

    def is_rejected(self) -> bool:
        """Check if checkpoint was rejected"""
        return self.status == "rejected"

    def has_decision(self) -> bool:
        """Check if user has made a decision"""
        return self.user_decision is not None
