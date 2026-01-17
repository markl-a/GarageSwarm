"""
SQLAlchemy Base Configuration

Declarative base and common base model for all database models.
"""

from uuid import uuid4

from sqlalchemy import TIMESTAMP, Column, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr

Base = declarative_base()


class BaseModel(Base):
    """
    Abstract base model with common fields.

    All models inherit from this to get:
    - UUID primary key
    - created_at timestamp
    - updated_at timestamp (auto-updated)
    """

    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name."""
        return cls.__name__.lower() + "s"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique identifier",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Record creation timestamp",
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Record last update timestamp",
    )

    def to_dict(self):
        """Convert model to dictionary."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"
