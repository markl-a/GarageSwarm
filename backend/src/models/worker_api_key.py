"""
Worker API Key Model

Secure API key storage for worker authentication.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, String, TIMESTAMP, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class WorkerAPIKey(Base):
    """Worker API Key model for authentication"""

    __tablename__ = "worker_api_keys"

    # Primary key
    key_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique API key identifier",
    )

    # Foreign key to worker
    worker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workers.worker_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated worker ID",
    )

    # Hashed API key (never store plain text)
    api_key_hash = Column(
        String(255),
        nullable=False,
        comment="Bcrypt-hashed API key",
    )

    # Key prefix for identification (first 12 chars of original key, e.g., 'wk_a1b2c3d4')
    key_prefix = Column(
        String(12),
        nullable=False,
        index=True,
        comment="Key prefix for identification",
    )

    # Description
    description = Column(
        Text,
        nullable=True,
        comment="Optional description for the API key",
    )

    # Status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether the key is active",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Key creation time",
    )

    expires_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Key expiration time (null = never expires)",
    )

    last_used_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Last time the key was used",
    )

    revoked_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the key was revoked",
    )

    # Created by (user who generated the key)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this key",
    )

    # Relationships
    worker = relationship("Worker", back_populates="api_keys")
    creator = relationship("User")

    def __repr__(self):
        return f"<WorkerAPIKey(key_id={self.key_id}, worker_id={self.worker_id}, prefix={self.key_prefix})>"

    def is_valid(self) -> bool:
        """Check if key is valid (active, not revoked, and not expired)"""
        if not self.is_active:
            return False
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < datetime.utcnow():
            return False
        return True
