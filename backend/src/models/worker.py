"""
Worker Model

Worker Agent registration, status tracking, and resource monitoring
"""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, Float, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Worker(Base):
    """Worker Agent model"""

    __tablename__ = "workers"

    # Primary key
    worker_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique worker identifier",
    )

    # Machine information
    machine_id = Column(
        String(100),
        unique=True,
        nullable=False,
        comment="Physical machine identifier (MAC address, hostname)",
    )

    machine_name = Column(
        String(100), nullable=False, comment="Human-readable machine name"
    )

    # Status
    status = Column(
        String(20),
        nullable=False,
        default="offline",
        index=True,
        comment="Worker status: online | offline | busy",
    )

    # System information (JSONB)
    system_info = Column(
        JSONB,
        nullable=False,
        comment="System info: {os, cpu, memory_total_gb, disk_total_gb}",
    )

    # Available AI tools (JSONB array)
    tools = Column(
        JSONB,
        nullable=False,
        comment='Available AI tools: ["claude_code", "gemini_cli", "ollama"]',
    )

    # Current resource usage
    cpu_percent = Column(Float, nullable=True, comment="Current CPU usage (0-100)")

    memory_percent = Column(Float, nullable=True, comment="Current memory usage (0-100)")

    disk_percent = Column(Float, nullable=True, comment="Current disk usage (0-100)")

    # Timestamps
    last_heartbeat = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True,
        comment="Last heartbeat received",
    )

    registered_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Registration time",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('online', 'offline', 'busy', 'idle')", name="chk_worker_status"
        ),
    )

    # Relationships
    subtasks = relationship("Subtask", back_populates="worker")
    proposals = relationship("Proposal", back_populates="worker")
    api_keys = relationship(
        "WorkerAPIKey", back_populates="worker", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Worker(worker_id={self.worker_id}, machine_name={self.machine_name}, status={self.status})>"

    def is_online(self) -> bool:
        """Check if worker is online"""
        return self.status == "online"

    def is_available(self) -> bool:
        """Check if worker is available for new tasks"""
        return self.status == "online"

    def has_tool(self, tool_name: str) -> bool:
        """Check if worker has a specific tool"""
        return tool_name in self.tools if self.tools else False
