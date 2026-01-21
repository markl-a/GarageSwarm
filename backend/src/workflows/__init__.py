"""
GarageSwarm Workflow System

Enhanced workflow execution with LangGraph-style state machine support.

Components:
- DAG Engine: Graph-based workflow execution
- Node Types: Task, Condition, Parallel, HumanReview, Loop
- State: Workflow state management
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
]
