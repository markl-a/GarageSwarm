"""
Activity Log Model

System-wide activity logging for debugging and auditing
"""

from sqlalchemy import BigInteger, Column, ForeignKey, String, TEXT, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class ActivityLog(Base):
    """Activity Log model - system-wide activity logging"""

    __tablename__ = "activity_logs"

    # Primary key
    log_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing log ID",
    )

    # Foreign keys (all nullable)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Related task ID",
    )

    subtask_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subtasks.subtask_id", ondelete="CASCADE"),
        nullable=True,
        comment="Related subtask ID",
    )

    worker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workers.worker_id"),
        nullable=True,
        comment="Related worker ID",
    )

    # Log details
    level = Column(
        String(10), nullable=False, comment="Log level: info | warning | error"
    )

    message = Column(TEXT, nullable=False, comment="Log message")

    log_metadata = Column(JSONB, nullable=True, comment="Additional structured data")

    # Timestamp
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Log timestamp",
    )

    # Relationships
    task = relationship("Task", back_populates="activity_logs")
    subtask = relationship("Subtask", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog(log_id={self.log_id}, level={self.level}, message={self.message[:50]}...)>"

    def is_info(self) -> bool:
        """Check if log is info level"""
        return self.level == "info"

    def is_warning(self) -> bool:
        """Check if log is warning level"""
        return self.level == "warning"

    def is_error(self) -> bool:
        """Check if log is error level"""
        return self.level == "error"
