"""
Correction Model

Store correction instructions from checkpoints for subtask rework
"""

from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Integer, String, TEXT, TIMESTAMP, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Correction(Base):
    """Correction model - correction instructions for subtask rework"""

    __tablename__ = "corrections"

    # Primary key
    correction_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique correction identifier",
    )

    # Foreign keys
    checkpoint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("checkpoints.checkpoint_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Related checkpoint ID",
    )

    subtask_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subtasks.subtask_id"),
        nullable=False,
        index=True,
        comment="Subtask to correct",
    )

    # Correction details
    correction_type = Column(
        String(20),
        nullable=False,
        comment="Correction type: wrong_approach | incomplete | bug | style | missing_feature | other",
    )

    guidance = Column(TEXT, nullable=False, comment="Correction instructions")

    reference_files = Column(
        JSONB,
        default=[],
        server_default=text("'[]'::jsonb"),
        comment="Reference files or links",
    )

    # Result
    result = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="Correction result: pending | success | failed",
    )

    retry_count = Column(Integer, default=0, nullable=False, comment="Number of retry attempts")

    # Learning mode
    apply_to_future = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Apply to future similar tasks",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Correction creation time",
    )

    resolved_at = Column(
        TIMESTAMP(timezone=True), nullable=True, comment="Correction resolution time"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "correction_type IN ('wrong_approach', 'incomplete', 'bug', 'style', 'missing_feature', 'other')",
            name="chk_correction_type",
        ),
        CheckConstraint(
            "result IN ('pending', 'success', 'failed')", name="chk_correction_result"
        ),
    )

    # Relationships
    checkpoint = relationship("Checkpoint", back_populates="corrections")
    subtask = relationship("Subtask", back_populates="corrections")

    def __repr__(self):
        return f"<Correction(correction_id={self.correction_id}, type={self.correction_type}, result={self.result})>"

    def is_pending(self) -> bool:
        """Check if correction is pending"""
        return self.result == "pending"

    def is_successful(self) -> bool:
        """Check if correction was successful"""
        return self.result == "success"

    def is_failed(self) -> bool:
        """Check if correction failed"""
        return self.result == "failed"

    def can_retry(self) -> bool:
        """Check if correction can be retried"""
        return self.retry_count < 3  # Max 3 retries
