"""
Workflow Models

DAG-based workflow engine supporting multiple execution patterns:
- Sequential: Linear pipeline
- Concurrent: Parallel execution
- Graph (DAG): Complex dependencies
- Hierarchical: Director + Workers
- Mixture: Multi-expert parallel
"""

from uuid import uuid4
import enum

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, TEXT, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import relationship

from .base import Base


class WorkflowType(str, enum.Enum):
    """Workflow execution pattern."""
    SEQUENTIAL = "sequential"      # Linear pipeline
    CONCURRENT = "concurrent"      # Parallel execution
    GRAPH = "graph"               # DAG with complex dependencies
    HIERARCHICAL = "hierarchical" # Director plans, workers execute
    MIXTURE = "mixture"           # Multi-expert parallel, aggregate output


class WorkflowStatus(str, enum.Enum):
    """Workflow execution status."""
    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(str, enum.Enum):
    """Workflow node types."""
    TASK = "task"                   # Execute AI task
    CONDITION = "condition"         # If/else branching
    PARALLEL_START = "parallel_start"  # Fork
    PARALLEL_END = "parallel_end"      # Join (wait all)
    WAIT = "wait"                   # Human approval
    ROUTER = "router"               # Dynamic routing
    DIRECTOR = "director"           # AI plans subtasks


class NodeStatus(str, enum.Enum):
    """Workflow node execution status."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Workflow(Base):
    """Workflow definition and execution state."""

    __tablename__ = "workflows"

    workflow_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique workflow identifier",
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workflow owner",
    )

    name = Column(
        String(200),
        nullable=False,
        comment="Workflow name",
    )

    description = Column(
        TEXT,
        nullable=True,
        comment="Workflow description",
    )

    workflow_type = Column(
        String(20),
        nullable=False,
        default=WorkflowType.SEQUENTIAL.value,
        comment="Execution pattern",
    )

    status = Column(
        String(20),
        nullable=False,
        default=WorkflowStatus.DRAFT.value,
        index=True,
        comment="Workflow status",
    )

    # DAG definition for graph-based workflows
    dag_definition = Column(
        JSONB,
        nullable=True,
        comment="DAG structure: {nodes: [...], edges: [...]}",
    )

    # Execution context
    context = Column(
        JSONB,
        nullable=True,
        comment="Shared context passed between nodes",
    )

    result = Column(
        JSONB,
        nullable=True,
        comment="Final workflow output",
    )

    error = Column(
        TEXT,
        nullable=True,
        comment="Error message if failed",
    )

    # Progress tracking
    total_nodes = Column(
        Integer,
        default=0,
        comment="Total nodes in workflow",
    )

    completed_nodes = Column(
        Integer,
        default=0,
        comment="Completed nodes count",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Creation time",
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update time",
    )

    started_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Execution start time",
    )

    completed_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Completion time",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "workflow_type IN ('sequential', 'concurrent', 'graph', 'hierarchical', 'mixture')",
            name="chk_workflow_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'pending', 'running', 'paused', 'completed', 'failed', 'cancelled')",
            name="chk_workflow_status",
        ),
    )

    # Relationships
    user = relationship("User", back_populates="workflows")
    nodes = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    edges = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="workflow")

    def __repr__(self):
        return f"<Workflow(workflow_id={self.workflow_id}, name={self.name}, status={self.status})>"

    @property
    def progress(self) -> int:
        """Calculate progress percentage."""
        if self.total_nodes == 0:
            return 0
        return int((self.completed_nodes / self.total_nodes) * 100)


class WorkflowNode(Base):
    """Individual node in a workflow."""

    __tablename__ = "workflow_nodes"

    node_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique node identifier",
    )

    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.workflow_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(
        String(200),
        nullable=False,
        comment="Node name",
    )

    node_type = Column(
        String(20),
        nullable=False,
        default=NodeType.TASK.value,
        comment="Node type",
    )

    status = Column(
        String(20),
        nullable=False,
        default=NodeStatus.PENDING.value,
        index=True,
        comment="Node execution status",
    )

    # Node configuration
    agent_config = Column(
        JSONB,
        nullable=True,
        comment="AI tool configuration: {tool, prompt, timeout, ...}",
    )

    condition_config = Column(
        JSONB,
        nullable=True,
        comment="Condition configuration for branching nodes",
    )

    # Execution order
    order_index = Column(
        Integer,
        default=0,
        comment="Execution order (for sequential workflows)",
    )

    # Dependencies (for DAG)
    dependencies = Column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True,
        comment="Node IDs this node depends on",
    )

    # Execution data
    input_data = Column(
        JSONB,
        nullable=True,
        comment="Input data for this node",
    )

    output = Column(
        JSONB,
        nullable=True,
        comment="Node execution output",
    )

    error = Column(
        TEXT,
        nullable=True,
        comment="Error message if failed",
    )

    # Retry handling
    retry_count = Column(
        Integer,
        default=0,
        comment="Number of retries attempted",
    )

    max_retries = Column(
        Integer,
        default=3,
        comment="Maximum retry attempts",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )

    started_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    completed_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "node_type IN ('task', 'condition', 'parallel_start', 'parallel_end', 'wait', 'router', 'director')",
            name="chk_node_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'ready', 'running', 'completed', 'failed', 'skipped')",
            name="chk_node_status",
        ),
    )

    # Relationships
    workflow = relationship("Workflow", back_populates="nodes")

    def __repr__(self):
        return f"<WorkflowNode(node_id={self.node_id}, name={self.name}, status={self.status})>"

    def is_ready(self) -> bool:
        """Check if node is ready for execution."""
        return self.status == NodeStatus.READY.value

    def can_retry(self) -> bool:
        """Check if node can be retried."""
        return self.retry_count < self.max_retries


class WorkflowEdge(Base):
    """Edge connecting two workflow nodes."""

    __tablename__ = "workflow_edges"

    edge_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
    )

    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.workflow_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_node_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
    )

    to_node_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
    )

    # Conditional edge
    condition = Column(
        JSONB,
        nullable=True,
        comment="Condition expression for this edge",
    )

    label = Column(
        String(100),
        nullable=True,
        comment="Edge label (e.g., 'true', 'false')",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    workflow = relationship("Workflow", back_populates="edges")

    def __repr__(self):
        return f"<WorkflowEdge(from={self.from_node_id}, to={self.to_node_id})>"
