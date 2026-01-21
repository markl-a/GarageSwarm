"""
Workflow Graph

DAG-based workflow structure for complex execution patterns.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from .nodes import BaseNode, NodeType, create_node


class WorkflowGraph(BaseModel):
    """
    Directed Acyclic Graph representation of a workflow.

    Supports:
    - Node management
    - Edge connections
    - Topological traversal
    - Entry/exit points
    """
    id: str
    name: str
    description: str = ""

    # Nodes
    nodes: Dict[str, BaseNode] = Field(default_factory=dict)

    # Edges (from_node -> [to_nodes])
    edges: Dict[str, List[str]] = Field(default_factory=lambda: defaultdict(list))

    # Special nodes
    entry_node: Optional[str] = None
    exit_nodes: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def add_node(self, node: BaseNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

        # Set entry if first node
        if len(self.nodes) == 1:
            self.entry_node = node.id

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add an edge between nodes."""
        if from_node not in self.nodes:
            raise ValueError(f"Source node not found: {from_node}")
        if to_node not in self.nodes:
            raise ValueError(f"Target node not found: {to_node}")

        if to_node not in self.edges[from_node]:
            self.edges[from_node].append(to_node)

        # Update node's next_nodes
        if to_node not in self.nodes[from_node].next_nodes:
            self.nodes[from_node].next_nodes.append(to_node)

    def remove_node(self, node_id: str) -> None:
        """Remove a node and its edges."""
        if node_id in self.nodes:
            del self.nodes[node_id]

        # Remove edges from this node
        if node_id in self.edges:
            del self.edges[node_id]

        # Remove edges to this node
        for source, targets in self.edges.items():
            if node_id in targets:
                targets.remove(node_id)

    def get_node(self, node_id: str) -> Optional[BaseNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_next_nodes(self, node_id: str) -> List[str]:
        """Get nodes that come after the given node."""
        return self.edges.get(node_id, [])

    def get_previous_nodes(self, node_id: str) -> List[str]:
        """Get nodes that come before the given node."""
        previous = []
        for source, targets in self.edges.items():
            if node_id in targets:
                previous.append(source)
        return previous

    def get_root_nodes(self) -> List[str]:
        """Get nodes with no incoming edges."""
        all_targets = set()
        for targets in self.edges.values():
            all_targets.update(targets)

        return [node_id for node_id in self.nodes if node_id not in all_targets]

    def get_leaf_nodes(self) -> List[str]:
        """Get nodes with no outgoing edges."""
        return [
            node_id for node_id in self.nodes
            if node_id not in self.edges or not self.edges[node_id]
        ]

    def topological_sort(self) -> List[str]:
        """
        Return nodes in topological order.

        Raises ValueError if graph has cycles.
        """
        in_degree = defaultdict(int)
        for node_id in self.nodes:
            in_degree[node_id] = 0

        for targets in self.edges.values():
            for target in targets:
                in_degree[target] += 1

        # Start with nodes that have no dependencies
        queue = [node_id for node_id in self.nodes if in_degree[node_id] == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for next_node in self.edges.get(node_id, []):
                in_degree[next_node] -= 1
                if in_degree[next_node] == 0:
                    queue.append(next_node)

        if len(result) != len(self.nodes):
            raise ValueError("Graph contains a cycle")

        return result

    def validate(self) -> List[str]:
        """
        Validate the graph structure.

        Returns list of validation errors.
        """
        errors = []

        # Check for entry node
        if not self.entry_node:
            errors.append("No entry node defined")
        elif self.entry_node not in self.nodes:
            errors.append(f"Entry node not found: {self.entry_node}")

        # Check for unreachable nodes
        reachable = self._get_reachable_nodes()
        unreachable = set(self.nodes.keys()) - reachable
        if unreachable:
            errors.append(f"Unreachable nodes: {unreachable}")

        # Check for cycles
        try:
            self.topological_sort()
        except ValueError as e:
            errors.append(str(e))

        # Validate node references
        for node_id, node in self.nodes.items():
            for next_node in node.next_nodes:
                if next_node not in self.nodes:
                    errors.append(f"Node {node_id} references non-existent node: {next_node}")

        return errors

    def _get_reachable_nodes(self) -> Set[str]:
        """Get all nodes reachable from entry."""
        if not self.entry_node:
            return set()

        reachable = set()
        to_visit = [self.entry_node]

        while to_visit:
            node_id = to_visit.pop()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            to_visit.extend(self.edges.get(node_id, []))

        return reachable

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": {
                node_id: node.model_dump()
                for node_id, node in self.nodes.items()
            },
            "edges": dict(self.edges),
            "entry_node": self.entry_node,
            "exit_nodes": self.exit_nodes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGraph":
        """Create graph from dictionary."""
        graph = cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", "")
        )

        # Add nodes
        for node_id, node_data in data.get("nodes", {}).items():
            node_type = node_data.get("node_type", NodeType.TASK)
            node = create_node(node_type, **node_data)
            graph.add_node(node)

        # Add edges
        for from_node, to_nodes in data.get("edges", {}).items():
            for to_node in to_nodes:
                graph.add_edge(from_node, to_node)

        graph.entry_node = data.get("entry_node")
        graph.exit_nodes = data.get("exit_nodes", [])

        return graph


def build_simple_chain(nodes: List[Dict[str, Any]], graph_id: str = "chain") -> WorkflowGraph:
    """
    Build a simple sequential chain of nodes.

    Helper for creating linear workflows.
    """
    graph = WorkflowGraph(id=graph_id, name=f"Chain-{graph_id}")

    prev_node = None
    for i, node_config in enumerate(nodes):
        node_config.setdefault("id", f"node_{i}")
        node_config.setdefault("name", f"Step {i + 1}")

        node_type = node_config.pop("node_type", NodeType.TASK)
        node = create_node(node_type, **node_config)
        graph.add_node(node)

        if prev_node:
            graph.add_edge(prev_node, node.id)

        prev_node = node.id

    return graph


def build_parallel_workflow(
    pre_node: Dict[str, Any],
    parallel_nodes: List[Dict[str, Any]],
    post_node: Dict[str, Any],
    graph_id: str = "parallel"
) -> WorkflowGraph:
    """
    Build a workflow with parallel branches.

    Structure:
    pre_node -> [parallel_nodes...] -> post_node
    """
    from .nodes import ParallelNode, JoinNode

    graph = WorkflowGraph(id=graph_id, name=f"Parallel-{graph_id}")

    # Pre node
    pre_node.setdefault("id", "pre")
    pre_type = pre_node.pop("node_type", NodeType.TASK)
    pre = create_node(pre_type, **pre_node)
    graph.add_node(pre)

    # Parallel split
    branch_ids = []
    parallel_split = ParallelNode(
        id="parallel_split",
        name="Parallel Split",
        branches=[]
    )
    graph.add_node(parallel_split)
    graph.add_edge(pre.id, parallel_split.id)

    # Parallel branches
    for i, branch_config in enumerate(parallel_nodes):
        branch_config.setdefault("id", f"branch_{i}")
        branch_config.setdefault("name", f"Branch {i + 1}")

        branch_type = branch_config.pop("node_type", NodeType.TASK)
        branch = create_node(branch_type, **branch_config)
        graph.add_node(branch)

        graph.add_edge(parallel_split.id, branch.id)
        branch_ids.append(branch.id)

    parallel_split.branches = branch_ids

    # Join node
    join = JoinNode(
        id="join",
        name="Join",
        join_mode="all"
    )
    graph.add_node(join)

    for branch_id in branch_ids:
        graph.add_edge(branch_id, join.id)

    # Post node
    post_node.setdefault("id", "post")
    post_type = post_node.pop("node_type", NodeType.TASK)
    post = create_node(post_type, **post_node)
    graph.add_node(post)
    graph.add_edge(join.id, post.id)

    return graph
