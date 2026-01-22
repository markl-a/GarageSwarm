"""
GarageSwarm Workflow System

Enhanced workflow execution with LangGraph-style state machine support.

Components:
- DAG Engine: Graph-based workflow execution
- Node Types: Task, Condition, Parallel, HumanReview, Loop
- State: Workflow state management
- Executor: Node execution with MCP Bus integration
- Checkpoints: Recovery and persistence
"""

from .nodes import (
    NodeType,
    BaseNode,
    TaskNode,
    ConditionNode,
    ParallelNode,
    JoinNode,
    HumanReviewNode,
    RouterNode,
    LoopNode,
    SubflowNode,
)
from .state import WorkflowState, WorkflowContext
from .graph import WorkflowGraph
from .executor import (
    NodeExecutor,
    ExecutionContext,
    ExecutionMetrics,
    ExecutorError,
    TaskExecutionError,
    ConditionEvaluationError,
    RouterDecisionError,
    TimeoutError,
)
from .checkpoints import (
    Checkpoint,
    CheckpointStore,
    CheckpointStorageBackend,
    RedisCheckpointBackend,
    get_checkpoint_store,
    create_checkpoint_store,
)

__all__ = [
    # Node Types
    "NodeType",
    "BaseNode",
    "TaskNode",
    "ConditionNode",
    "ParallelNode",
    "JoinNode",
    "HumanReviewNode",
    "RouterNode",
    "LoopNode",
    "SubflowNode",
    # State
    "WorkflowState",
    "WorkflowContext",
    # Graph
    "WorkflowGraph",
    # Executor
    "NodeExecutor",
    "ExecutionContext",
    "ExecutionMetrics",
    "ExecutorError",
    "TaskExecutionError",
    "ConditionEvaluationError",
    "RouterDecisionError",
    "TimeoutError",
    # Checkpoints
    "Checkpoint",
    "CheckpointStore",
    "CheckpointStorageBackend",
    "RedisCheckpointBackend",
    "get_checkpoint_store",
    "create_checkpoint_store",
]
