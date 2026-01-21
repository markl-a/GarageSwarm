"""
Workflow State Management

Manages workflow execution state with:
- State persistence
- State updates and merging
- Parallel result aggregation
- Checkpoint support
"""

import copy
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowContext(BaseModel):
    """
    Context passed to workflow execution.

    Contains metadata and configuration that doesn't change during execution.
    """
    workflow_id: UUID
    workflow_name: str
    user_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Configuration
    timeout: float = 3600.0  # 1 hour default
    max_retries: int = 3
    debug: bool = False

    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    """
    Mutable workflow state that evolves during execution.

    Stores:
    - Node outputs
    - Execution progress
    - Intermediate results
    - Error information
    """
    # Initial input
    input: Dict[str, Any] = Field(default_factory=dict)

    # Node outputs (node_id -> output)
    outputs: Dict[str, Any] = Field(default_factory=dict)

    # Current execution pointer
    current_node: Optional[str] = None
    completed_nodes: Set[str] = Field(default_factory=set)
    failed_nodes: Set[str] = Field(default_factory=set)

    # Parallel execution tracking
    parallel_branches: Dict[str, Set[str]] = Field(default_factory=dict)  # join_id -> branch_ids
    parallel_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # join_id -> {branch_id: result}

    # Loop tracking
    loop_iterations: Dict[str, int] = Field(default_factory=dict)  # loop_node_id -> iteration

    # Human review
    pending_reviews: List[str] = Field(default_factory=list)  # node_ids waiting for review

    # Error tracking
    errors: List[Dict[str, Any]] = Field(default_factory=list)

    # Timestamps
    started_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True

    def update(self, key: str, value: Any) -> None:
        """Update a single output value."""
        self.outputs[key] = value
        self.last_updated = datetime.utcnow()

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from outputs or input."""
        if key in self.outputs:
            return self.outputs[key]
        if key in self.input:
            return self.input[key]
        return default

    def merge(self, other: Dict[str, Any]) -> None:
        """Merge dictionary into outputs."""
        self.outputs.update(other)
        self.last_updated = datetime.utcnow()

    def mark_completed(self, node_id: str, output: Any = None) -> None:
        """Mark a node as completed."""
        self.completed_nodes.add(node_id)
        if node_id in self.failed_nodes:
            self.failed_nodes.remove(node_id)
        if output is not None:
            self.outputs[node_id] = output
        self.last_updated = datetime.utcnow()

    def mark_failed(self, node_id: str, error: str) -> None:
        """Mark a node as failed."""
        self.failed_nodes.add(node_id)
        self.errors.append({
            "node_id": node_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.last_updated = datetime.utcnow()

    def start_parallel(self, join_id: str, branch_ids: List[str]) -> None:
        """Start tracking parallel branches."""
        self.parallel_branches[join_id] = set(branch_ids)
        self.parallel_results[join_id] = {}

    def complete_branch(self, join_id: str, branch_id: str, result: Any) -> bool:
        """
        Record completion of a parallel branch.

        Returns True if all branches are complete.
        """
        if join_id not in self.parallel_results:
            self.parallel_results[join_id] = {}

        self.parallel_results[join_id][branch_id] = result

        # Check if all branches complete
        expected = self.parallel_branches.get(join_id, set())
        completed = set(self.parallel_results[join_id].keys())

        return expected == completed

    def get_parallel_results(self, join_id: str) -> Dict[str, Any]:
        """Get results from all parallel branches."""
        return self.parallel_results.get(join_id, {})

    def increment_loop(self, loop_id: str) -> int:
        """Increment loop iteration counter."""
        current = self.loop_iterations.get(loop_id, 0)
        self.loop_iterations[loop_id] = current + 1
        return self.loop_iterations[loop_id]

    def reset_loop(self, loop_id: str) -> None:
        """Reset loop iteration counter."""
        self.loop_iterations.pop(loop_id, None)

    def add_pending_review(self, node_id: str) -> None:
        """Add node to pending reviews."""
        if node_id not in self.pending_reviews:
            self.pending_reviews.append(node_id)

    def complete_review(self, node_id: str) -> None:
        """Remove node from pending reviews."""
        if node_id in self.pending_reviews:
            self.pending_reviews.remove(node_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "input": self.input,
            "outputs": self.outputs,
            "current_node": self.current_node,
            "completed_nodes": list(self.completed_nodes),
            "failed_nodes": list(self.failed_nodes),
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_updated": self.last_updated.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """Create from dictionary."""
        data = copy.deepcopy(data)
        if "completed_nodes" in data:
            data["completed_nodes"] = set(data["completed_nodes"])
        if "failed_nodes" in data:
            data["failed_nodes"] = set(data["failed_nodes"])
        if "started_at" in data and data["started_at"]:
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if "last_updated" in data:
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        return cls(**data)

    def clone(self) -> "WorkflowState":
        """Create a deep copy of state."""
        return WorkflowState(
            input=copy.deepcopy(self.input),
            outputs=copy.deepcopy(self.outputs),
            current_node=self.current_node,
            completed_nodes=self.completed_nodes.copy(),
            failed_nodes=self.failed_nodes.copy(),
            parallel_branches={k: v.copy() for k, v in self.parallel_branches.items()},
            parallel_results=copy.deepcopy(self.parallel_results),
            loop_iterations=self.loop_iterations.copy(),
            pending_reviews=self.pending_reviews.copy(),
            errors=copy.deepcopy(self.errors),
            started_at=self.started_at,
            last_updated=self.last_updated
        )
