"""
Workflow Node Types

Defines different node types for workflow execution:
- Task: Execute an AI tool
- Condition: Branching based on state
- Parallel: Execute multiple branches concurrently
- Join: Wait for parallel branches
- HumanReview: Pause for human approval
- Router: Dynamic routing based on LLM
- Loop: Repeat until condition
- Subflow: Nested workflow
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of workflow nodes."""
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    JOIN = "join"
    HUMAN_REVIEW = "human_review"
    ROUTER = "router"
    LOOP = "loop"
    SUBFLOW = "subflow"
    WAIT = "wait"
    START = "start"
    END = "end"


class NodeStatus(str, Enum):
    """Execution status of a node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"  # For human review or external events


class BaseNode(BaseModel, ABC):
    """
    Base class for all workflow nodes.

    All nodes have:
    - Unique ID
    - Type
    - Name
    - Input/output handling
    - Retry configuration
    """
    id: str
    node_type: NodeType
    name: str
    description: str = ""

    # Execution state
    status: NodeStatus = NodeStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    # Input/Output
    input_mapping: Dict[str, str] = Field(default_factory=dict)  # state_key -> node_input_key
    output_key: str = "result"  # Key to store output in state

    # Retry configuration
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0

    # Next nodes (for graph building)
    next_nodes: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def resolve_inputs(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve input values from workflow state."""
        if not self.input_mapping:
            return state.copy()

        resolved = {}
        for state_key, input_key in self.input_mapping.items():
            if state_key in state:
                resolved[input_key] = state[state_key]
        return resolved

    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Any:
        """Execute the node and return output."""
        pass


class TaskNode(BaseNode):
    """
    Task node - executes an AI tool.

    Configuration:
    - tool_path: MCP tool path (server.tool_name)
    - arguments: Static arguments
    - timeout: Execution timeout
    """
    node_type: NodeType = NodeType.TASK

    # Task configuration
    tool_path: str = ""  # e.g., "ollama.generate"
    arguments: Dict[str, Any] = Field(default_factory=dict)
    timeout: float = 60.0

    # For direct agent execution (legacy support)
    agent_config: Dict[str, Any] = Field(default_factory=dict)

    async def execute(self, state: Dict[str, Any]) -> Any:
        """
        Execute task via MCP.

        This is a placeholder - actual execution is handled by the engine.
        """
        # Will be replaced by engine's actual execution
        return {"status": "executed", "node": self.name}


class ConditionNode(BaseNode):
    """
    Condition node - branches based on state evaluation.

    Supports:
    - Simple comparisons (==, !=, <, >, etc.)
    - Path expressions for nested values
    - Multiple conditions (all must pass for true branch)
    """
    node_type: NodeType = NodeType.CONDITION

    # Condition configuration
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    # Format: [{"field": "result.status", "operator": "==", "value": "success"}]

    # Branch targets
    true_branch: str = ""  # Node ID if condition is true
    false_branch: str = ""  # Node ID if condition is false

    async def execute(self, state: Dict[str, Any]) -> Any:
        """Evaluate condition and return branch target."""
        result = self.evaluate(state)
        return {
            "branch": self.true_branch if result else self.false_branch,
            "condition_result": result
        }

    def evaluate(self, state: Dict[str, Any]) -> bool:
        """Evaluate all conditions against state."""
        if not self.conditions:
            return True

        for condition in self.conditions:
            field = condition.get("field", "")
            operator = condition.get("operator", "==")
            expected = condition.get("value")

            actual = self._get_nested_value(state, field)

            if not self._compare(actual, operator, expected):
                return False

        return True

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation."""
        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        """Compare values using operator."""
        if operator == "==":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        elif operator == "<":
            return actual < expected
        elif operator == ">":
            return actual > expected
        elif operator == "<=":
            return actual <= expected
        elif operator == ">=":
            return actual >= expected
        elif operator == "in":
            return actual in expected
        elif operator == "not_in":
            return actual not in expected
        elif operator == "contains":
            return expected in actual
        elif operator == "is_none":
            return actual is None
        elif operator == "is_not_none":
            return actual is not None
        elif operator == "is_true":
            return bool(actual)
        elif operator == "is_false":
            return not bool(actual)
        else:
            return False


class ParallelNode(BaseNode):
    """
    Parallel node - executes multiple branches concurrently.

    All branches start simultaneously.
    Use JoinNode to wait for all/any branches to complete.
    """
    node_type: NodeType = NodeType.PARALLEL

    # Branches to execute in parallel
    branches: List[str] = Field(default_factory=list)  # List of node IDs

    # Configuration
    fail_fast: bool = False  # Stop all branches on first failure

    async def execute(self, state: Dict[str, Any]) -> Any:
        """Return branches to execute."""
        return {
            "parallel_branches": self.branches,
            "fail_fast": self.fail_fast
        }


class JoinNode(BaseNode):
    """
    Join node - waits for parallel branches to complete.

    Modes:
    - all: Wait for all branches
    - any: Continue when any branch completes
    - n_of_m: Continue when N branches complete
    """
    node_type: NodeType = NodeType.JOIN

    # Join configuration
    join_mode: str = "all"  # "all", "any", "n_of_m"
    required_count: int = 1  # For n_of_m mode

    # Merge strategy
    merge_strategy: str = "dict"  # "dict", "list", "first", "last"

    async def execute(self, state: Dict[str, Any]) -> Any:
        """Merge parallel results."""
        parallel_results = state.get("_parallel_results", {})

        if self.merge_strategy == "dict":
            return parallel_results
        elif self.merge_strategy == "list":
            return list(parallel_results.values())
        elif self.merge_strategy == "first":
            return next(iter(parallel_results.values()), None)
        elif self.merge_strategy == "last":
            return list(parallel_results.values())[-1] if parallel_results else None
        else:
            return parallel_results


class HumanReviewNode(BaseNode):
    """
    Human review node - pauses workflow for human approval.

    Workflow pauses until human provides decision:
    - approve: Continue with optional modifications
    - reject: Cancel workflow or take alternate path
    - modify: Update state before continuing
    """
    node_type: NodeType = NodeType.HUMAN_REVIEW

    # Review configuration
    review_type: str = "approval"  # "approval", "input", "selection"
    instructions: str = ""
    required_fields: List[str] = Field(default_factory=list)

    # Timeout
    timeout_hours: float = 24.0  # Max wait time
    timeout_action: str = "reject"  # What to do on timeout

    # Branch targets
    approve_branch: str = ""
    reject_branch: str = ""

    # Urgency for notifications
    urgency: str = "normal"  # "low", "normal", "high", "critical"

    async def execute(self, state: Dict[str, Any]) -> Any:
        """Return review request - actual pausing handled by engine."""
        return {
            "waiting_for_review": True,
            "review_type": self.review_type,
            "instructions": self.instructions,
            "required_fields": self.required_fields
        }


class RouterNode(BaseNode):
    """
    Router node - dynamic routing based on LLM decision.

    Uses an LLM to analyze state and decide which branch to take.
    Useful for complex routing that can't be expressed as simple conditions.
    """
    node_type: NodeType = NodeType.ROUTER

    # Router configuration
    routing_prompt: str = ""  # Prompt for LLM to decide routing
    routes: Dict[str, str] = Field(default_factory=dict)  # label -> node_id
    default_route: str = ""

    # LLM configuration
    model: str = "ollama"  # Which model to use for routing

    async def execute(self, state: Dict[str, Any]) -> Any:
        """Return routing decision - actual LLM call handled by engine."""
        return {
            "needs_routing": True,
            "routing_prompt": self.routing_prompt,
            "available_routes": self.routes
        }


class LoopNode(BaseNode):
    """
    Loop node - repeats until condition is met.

    Executes body nodes repeatedly until:
    - Condition becomes true/false
    - Max iterations reached
    - Break signal in state
    """
    node_type: NodeType = NodeType.LOOP

    # Loop configuration
    condition: Dict[str, Any] = Field(default_factory=dict)  # Same as ConditionNode
    continue_on_true: bool = True  # Loop while condition is true

    # Body
    body_node: str = ""  # First node of loop body
    after_loop: str = ""  # Node after loop exits

    # Limits
    max_iterations: int = 100
    current_iteration: int = 0

    async def execute(self, state: Dict[str, Any]) -> Any:
        """Evaluate loop condition and return next action."""
        self.current_iteration += 1

        # Check max iterations
        if self.current_iteration > self.max_iterations:
            return {
                "loop_action": "exit",
                "next_node": self.after_loop,
                "reason": "max_iterations"
            }

        # Check break signal
        if state.get("_break_loop"):
            return {
                "loop_action": "exit",
                "next_node": self.after_loop,
                "reason": "break_signal"
            }

        # Evaluate condition
        condition_met = self._evaluate_condition(state)
        should_continue = condition_met if self.continue_on_true else not condition_met

        if should_continue:
            return {
                "loop_action": "continue",
                "next_node": self.body_node,
                "iteration": self.current_iteration
            }
        else:
            return {
                "loop_action": "exit",
                "next_node": self.after_loop,
                "reason": "condition"
            }

    def _evaluate_condition(self, state: Dict[str, Any]) -> bool:
        """Evaluate loop condition."""
        if not self.condition:
            return True

        # Reuse ConditionNode logic
        cond = ConditionNode(
            id="temp",
            name="loop_condition",
            conditions=[self.condition]
        )
        return cond.evaluate(state)


class SubflowNode(BaseNode):
    """
    Subflow node - executes a nested workflow.

    Allows composing complex workflows from reusable components.
    """
    node_type: NodeType = NodeType.SUBFLOW

    # Subflow configuration
    workflow_id: Optional[UUID] = None  # Reference to another workflow
    workflow_template: Optional[str] = None  # Or template name

    # Input/output mapping
    subflow_inputs: Dict[str, str] = Field(default_factory=dict)
    subflow_outputs: Dict[str, str] = Field(default_factory=dict)

    # Behavior
    inherit_state: bool = False  # Pass full parent state

    async def execute(self, state: Dict[str, Any]) -> Any:
        """Return subflow execution request - actual execution handled by engine."""
        return {
            "execute_subflow": True,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "workflow_template": self.workflow_template
        }


# Node factory
def create_node(node_type: Union[NodeType, str], **kwargs) -> BaseNode:
    """
    Factory function to create nodes.

    Args:
        node_type: Type of node to create
        **kwargs: Node configuration

    Returns:
        Configured node instance
    """
    if isinstance(node_type, str):
        node_type = NodeType(node_type)

    node_classes = {
        NodeType.TASK: TaskNode,
        NodeType.CONDITION: ConditionNode,
        NodeType.PARALLEL: ParallelNode,
        NodeType.JOIN: JoinNode,
        NodeType.HUMAN_REVIEW: HumanReviewNode,
        NodeType.ROUTER: RouterNode,
        NodeType.LOOP: LoopNode,
        NodeType.SUBFLOW: SubflowNode,
    }

    node_class = node_classes.get(node_type)
    if not node_class:
        raise ValueError(f"Unknown node type: {node_type}")

    return node_class(**kwargs)
