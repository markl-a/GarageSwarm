"""
User-Worker Relationship Model

Many-to-many relationship between users and workers with role-based access.
"""

from uuid import uuid4

from sqlalchemy import Column, String, TIMESTAMP, Boolean, ForeignKey, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from .base import Base


class WorkerRole(str, enum.Enum):
    """Role for user-worker relationship."""
    OWNER = "owner"       # Full control, can delete worker
    OPERATOR = "operator" # Can assign tasks, view status
    VIEWER = "viewer"     # Read-only access


class UserWorker(Base):
    """User-Worker association with role-based access."""

    __tablename__ = "user_workers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    worker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workers.worker_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(
        String(20),
        nullable=False,
        default=WorkerRole.VIEWER.value,
        comment="User role for this worker: owner | operator | viewer",
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this association is active",
    )

    added_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="When user was added to worker",
    )

    # Relationships
    user = relationship("User", back_populates="worker_associations")
    worker = relationship("Worker", back_populates="user_associations")

    def __repr__(self):
        return f"<UserWorker(user_id={self.user_id}, worker_id={self.worker_id}, role={self.role})>"

    def can_assign_tasks(self) -> bool:
        """Check if user can assign tasks to this worker."""
        return self.role in (WorkerRole.OWNER.value, WorkerRole.OPERATOR.value)

    def can_delete_worker(self) -> bool:
        """Check if user can delete this worker."""
        return self.role == WorkerRole.OWNER.value
