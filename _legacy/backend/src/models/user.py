"""
User Model

User authentication and account management (Future feature - MVP uses simple auth)
"""

from uuid import uuid4

from sqlalchemy import Column, String, TIMESTAMP, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    """User account model"""

    __tablename__ = "users"

    # Primary key
    user_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique user identifier",
    )

    # Authentication
    username = Column(
        String(50), unique=True, nullable=False, comment="Username for login"
    )

    email = Column(
        String(255), unique=True, nullable=False, index=True, comment="User email address"
    )

    password_hash = Column(
        String(255), nullable=False, comment="Hashed password (bcrypt)"
    )

    is_active = Column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="Whether user account is active",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Account creation time",
    )

    last_login = Column(
        TIMESTAMP(timezone=True), nullable=True, comment="Last login timestamp"
    )

    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    templates = relationship("WorkflowTemplate", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"
