"""Task Decomposer Service - Decomposes tasks into subtasks using rule-based engine"""

from collections import defaultdict, deque
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from src.models.task import Task
from src.models.subtask import Subtask
from src.services.redis_service import RedisService
from src.exceptions import CycleDetectedError
from src.schemas.task import TaskStatus
from src.schemas.subtask import SubtaskStatus

logger = structlog.get_logger()


def detect_cycle_in_dag(
    nodes: List[str],
    dependencies: Dict[str, List[str]]
) -> Tuple[bool, Optional[List[str]]]:
    """
    Detect cycles in a Directed Acyclic Graph using Kahn's algorithm.

    Args:
        nodes: List of node identifiers (subtask names or IDs)
        dependencies: Dict mapping node -> list of nodes it depends on

    Returns:
        Tuple of (has_cycle, cycle_path)
        - has_cycle: True if a cycle is detected
        - cycle_path: List of nodes forming the cycle (if detected), None otherwise

    Example:
        nodes = ["A", "B", "C"]
        dependencies = {"B": ["A"], "C": ["B"], "A": ["C"]}  # A->B->C->A cycle
        has_cycle, path = detect_cycle_in_dag(nodes, dependencies)
        # has_cycle = True, path = ["A", "C", "B", "A"]
    """
    # Build adjacency list (reverse direction: node -> dependents)
    graph: Dict[str, List[str]] = defaultdict(list)
    in_degree: Dict[str, int] = {node: 0 for node in nodes}

    for node, deps in dependencies.items():
        for dep in deps:
            if dep in in_degree:  # Only count valid dependencies
                graph[dep].append(node)
                in_degree[node] += 1

    # Kahn's algorithm - find nodes with no incoming edges
    queue = deque([node for node, degree in in_degree.items() if degree == 0])
    processed = []

    while queue:
        node = queue.popleft()
        processed.append(node)

        for dependent in graph[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # If not all nodes processed, there's a cycle
    if len(processed) != len(nodes):
        # Find the cycle using DFS
        remaining = set(nodes) - set(processed)
        cycle_path = _find_cycle_path(remaining, dependencies)
        return True, cycle_path

    return False, None


def _find_cycle_path(
    nodes: Set[str],
    dependencies: Dict[str, List[str]]
) -> List[str]:
    """
    Find the actual cycle path using DFS.

    Args:
        nodes: Set of nodes that are part of cycle(s)
        dependencies: Dependency mapping

    Returns:
        List of nodes forming one cycle
    """
    visited: Set[str] = set()
    path: List[str] = []
    path_set: Set[str] = set()

    def dfs(node: str) -> Optional[List[str]]:
        if node in path_set:
            # Found cycle - extract it
            cycle_start = path.index(node)
            return path[cycle_start:] + [node]

        if node in visited:
            return None

        visited.add(node)
        path.append(node)
        path_set.add(node)

        for dep in dependencies.get(node, []):
            if dep in nodes:
                result = dfs(dep)
                if result:
                    return result

        path.pop()
        path_set.remove(node)
        return None

    for start_node in nodes:
        if start_node not in visited:
            result = dfs(start_node)
            if result:
                return result

    return list(nodes)[:5]  # Fallback: return some cycle nodes


# Subtask type definitions for different task types
SUBTASK_DEFINITIONS = {
    "develop_feature": [
        {
            "name": "Code Generation",
            "description": "Generate the main code implementation based on requirements",
            "recommended_tool": "claude_code",
            "complexity": 3,
            "priority": 100,
            "dependencies": [],
        },
        {
            "name": "Code Review",
            "description": "Review generated code for quality, security, and best practices",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 80,
            "dependencies": ["Code Generation"],
        },
        {
            "name": "Test Generation",
            "description": "Generate unit tests and integration tests for the code",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 70,
            "dependencies": ["Code Generation"],
        },
        {
            "name": "Documentation",
            "description": "Generate documentation including docstrings and README updates",
            "recommended_tool": "claude_code",
            "complexity": 1,
            "priority": 50,
            "dependencies": ["Code Review", "Test Generation"],
        },
    ],
    "bug_fix": [
        {
            "name": "Bug Analysis",
            "description": "Analyze the bug report and identify root cause",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 100,
            "dependencies": [],
        },
        {
            "name": "Fix Implementation",
            "description": "Implement the bug fix based on analysis",
            "recommended_tool": "claude_code",
            "complexity": 3,
            "priority": 90,
            "dependencies": ["Bug Analysis"],
        },
        {
            "name": "Regression Testing",
            "description": "Create regression tests to prevent future occurrences",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 80,
            "dependencies": ["Fix Implementation"],
        },
    ],
    "refactor": [
        {
            "name": "Code Analysis",
            "description": "Analyze existing code structure and identify refactoring opportunities",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 100,
            "dependencies": [],
        },
        {
            "name": "Refactoring",
            "description": "Perform the refactoring while maintaining functionality",
            "recommended_tool": "claude_code",
            "complexity": 4,
            "priority": 90,
            "dependencies": ["Code Analysis"],
        },
        {
            "name": "Test Verification",
            "description": "Verify all existing tests still pass after refactoring",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 80,
            "dependencies": ["Refactoring"],
        },
    ],
    "code_review": [
        {
            "name": "Static Analysis",
            "description": "Perform static code analysis for potential issues",
            "recommended_tool": "claude_code",
            "complexity": 1,
            "priority": 100,
            "dependencies": [],
        },
        {
            "name": "Security Review",
            "description": "Review code for security vulnerabilities",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 90,
            "dependencies": [],
        },
        {
            "name": "Review Report",
            "description": "Generate comprehensive code review report",
            "recommended_tool": "claude_code",
            "complexity": 1,
            "priority": 80,
            "dependencies": ["Static Analysis", "Security Review"],
        },
    ],
    "documentation": [
        {
            "name": "API Documentation",
            "description": "Generate or update API documentation",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 100,
            "dependencies": [],
        },
        {
            "name": "User Guide",
            "description": "Create or update user documentation",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 90,
            "dependencies": [],
        },
        {
            "name": "README Update",
            "description": "Update README with latest information",
            "recommended_tool": "claude_code",
            "complexity": 1,
            "priority": 80,
            "dependencies": ["API Documentation", "User Guide"],
        },
    ],
    "testing": [
        {
            "name": "Test Planning",
            "description": "Create test plan and identify test cases",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 100,
            "dependencies": [],
        },
        {
            "name": "Unit Test Implementation",
            "description": "Implement unit tests",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 90,
            "dependencies": ["Test Planning"],
        },
        {
            "name": "Integration Test Implementation",
            "description": "Implement integration tests",
            "recommended_tool": "claude_code",
            "complexity": 3,
            "priority": 80,
            "dependencies": ["Test Planning"],
        },
        {
            "name": "Test Execution Report",
            "description": "Execute tests and generate report",
            "recommended_tool": "claude_code",
            "complexity": 1,
            "priority": 70,
            "dependencies": ["Unit Test Implementation", "Integration Test Implementation"],
        },
    ],
}


class TaskDecomposer:
    """
    Service for decomposing tasks into subtasks using a rule-based engine.

    The decomposer uses predefined templates based on task_type to generate
    subtasks with proper dependencies forming a DAG (Directed Acyclic Graph).
    """

    def __init__(self, db: AsyncSession, redis_service: RedisService):
        """Initialize TaskDecomposer

        Args:
            db: Database session
            redis_service: Redis service instance
        """
        self.db = db
        self.redis = redis_service

    async def decompose_task(self, task_id: UUID) -> List[Subtask]:
        """
        Decompose a task into subtasks based on its type.

        Args:
            task_id: Task UUID to decompose

        Returns:
            List of created subtasks

        Raises:
            ValueError: If task not found or already decomposed
        """
        logger.info("Decomposing task", task_id=str(task_id))

        # Get task
        result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Check if task already has subtasks
        existing_subtasks = await self.db.execute(
            select(Subtask).where(Subtask.task_id == task_id)
        )
        if existing_subtasks.scalars().first():
            raise ValueError(f"Task {task_id} already has subtasks")

        # Get task type from metadata
        task_type = self._get_task_type(task)

        # Get subtask definitions
        subtask_defs = SUBTASK_DEFINITIONS.get(task_type, SUBTASK_DEFINITIONS["develop_feature"])

        # Create subtasks
        subtasks = await self._create_subtasks(task, subtask_defs)

        # Update task status to initializing
        task.status = TaskStatus.INITIALIZING.value

        # Store estimated subtask count in metadata
        if task.task_metadata is None:
            task.task_metadata = {}
        task.task_metadata["estimated_subtasks"] = len(subtasks)

        await self.db.commit()

        # Update Redis
        await self.redis.set_task_status(task_id, "initializing")

        logger.info(
            "Task decomposed successfully",
            task_id=str(task_id),
            subtask_count=len(subtasks)
        )

        return subtasks

    def _get_task_type(self, task: Task) -> str:
        """Extract task type from task metadata

        Args:
            task: Task instance

        Returns:
            Task type string (defaults to 'develop_feature')
        """
        if task.task_metadata and "task_type" in task.task_metadata:
            return task.task_metadata["task_type"]
        return "develop_feature"

    async def _create_subtasks(
        self,
        task: Task,
        subtask_defs: List[Dict[str, Any]]
    ) -> List[Subtask]:
        """
        Create subtasks from definitions with proper dependency resolution.

        Args:
            task: Parent task
            subtask_defs: List of subtask definitions

        Returns:
            List of created subtasks

        Raises:
            CycleDetectedError: If circular dependencies are detected
        """
        # Validate DAG structure BEFORE creating any subtasks
        self._validate_dag(subtask_defs)

        # First pass: create all subtasks with placeholder dependencies
        name_to_subtask: Dict[str, Subtask] = {}
        subtasks: List[Subtask] = []

        for subtask_def in subtask_defs:
            subtask = Subtask(
                task_id=task.task_id,
                name=subtask_def["name"],
                description=self._enhance_description(
                    subtask_def["description"],
                    task.description
                ),
                recommended_tool=subtask_def.get("recommended_tool"),
                complexity=subtask_def.get("complexity", 2),
                priority=subtask_def.get("priority", 50),
                dependencies=[],  # Will be set in second pass
                status="pending",
                progress=0,
            )
            self.db.add(subtask)
            subtasks.append(subtask)
            name_to_subtask[subtask_def["name"]] = subtask

        # Flush to get subtask IDs
        await self.db.flush()

        # Second pass: resolve dependencies by name to UUID
        for subtask_def in subtask_defs:
            subtask = name_to_subtask[subtask_def["name"]]
            dep_names = subtask_def.get("dependencies", [])

            if dep_names:
                dep_ids = [
                    str(name_to_subtask[dep_name].subtask_id)
                    for dep_name in dep_names
                    if dep_name in name_to_subtask
                ]
                subtask.dependencies = dep_ids

        # Refresh all subtasks
        for subtask in subtasks:
            await self.db.refresh(subtask)

        return subtasks

    def _validate_dag(self, subtask_defs: List[Dict[str, Any]]) -> None:
        """
        Validate that subtask definitions form a valid DAG (no cycles).

        Args:
            subtask_defs: List of subtask definitions

        Raises:
            CycleDetectedError: If circular dependencies are detected
        """
        # Extract nodes and dependencies
        nodes = [subtask_def["name"] for subtask_def in subtask_defs]
        dependencies = {
            subtask_def["name"]: subtask_def.get("dependencies", [])
            for subtask_def in subtask_defs
        }

        # Check for self-dependencies
        for name, deps in dependencies.items():
            if name in deps:
                raise CycleDetectedError(
                    message=f"Subtask '{name}' depends on itself",
                    cycle_path=[name, name]
                )

        # Check for cycles using Kahn's algorithm
        has_cycle, cycle_path = detect_cycle_in_dag(nodes, dependencies)

        if has_cycle:
            logger.error(
                "Circular dependency detected in subtask DAG",
                cycle_path=cycle_path
            )
            raise CycleDetectedError(
                message="Circular dependency detected in subtask definitions",
                cycle_path=cycle_path
            )

    def _enhance_description(self, base_description: str, task_description: str) -> str:
        """
        Enhance subtask description with context from parent task.

        Args:
            base_description: Template description
            task_description: Parent task description

        Returns:
            Enhanced description
        """
        # Truncate task description if too long
        context = task_description[:500] if len(task_description) > 500 else task_description
        return f"{base_description}\n\nTask Context:\n{context}"

    async def get_ready_subtasks(self, task_id: UUID) -> List[Subtask]:
        """
        Get subtasks that are ready to execute (no pending dependencies).

        Args:
            task_id: Parent task UUID

        Returns:
            List of subtasks ready for execution
        """
        # Get all subtasks for the task
        result = await self.db.execute(
            select(Subtask)
            .where(Subtask.task_id == task_id)
            .where(Subtask.status == SubtaskStatus.PENDING.value)
        )
        pending_subtasks = result.scalars().all()

        # Get completed subtask IDs
        completed_result = await self.db.execute(
            select(Subtask.subtask_id)
            .where(Subtask.task_id == task_id)
            .where(Subtask.status == SubtaskStatus.COMPLETED.value)
        )
        completed_ids = {str(row[0]) for row in completed_result.fetchall()}

        # Filter subtasks with all dependencies satisfied
        ready_subtasks = []
        for subtask in pending_subtasks:
            deps = subtask.dependencies or []
            if all(dep_id in completed_ids for dep_id in deps):
                ready_subtasks.append(subtask)

        return ready_subtasks

    async def check_task_completion(self, task_id: UUID) -> bool:
        """
        Check if all subtasks are completed and update task status.

        Args:
            task_id: Task UUID

        Returns:
            True if task is completed
        """
        # Count subtasks by status
        result = await self.db.execute(
            select(Subtask).where(Subtask.task_id == task_id)
        )
        subtasks = result.scalars().all()

        if not subtasks:
            return False

        total = len(subtasks)
        completed = sum(1 for s in subtasks if s.status == SubtaskStatus.COMPLETED.value)
        failed = sum(1 for s in subtasks if s.status == SubtaskStatus.FAILED.value)

        # Calculate progress
        progress = int((completed / total) * 100) if total > 0 else 0

        # Get task
        task_result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = task_result.scalar_one_or_none()

        if not task:
            return False

        # Update task progress
        task.progress = progress

        # Check completion status
        if failed > 0:
            task.status = TaskStatus.FAILED.value
            task.completed_at = datetime.utcnow()
            await self.db.commit()
            await self.redis.set_task_status(task_id, TaskStatus.FAILED.value)
            await self.redis.set_task_progress(task_id, progress)
            return True
        elif completed == total:
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.utcnow()
            await self.db.commit()
            await self.redis.set_task_status(task_id, TaskStatus.COMPLETED.value)
            await self.redis.set_task_progress(task_id, 100)
            return True
        else:
            # Still in progress
            await self.db.commit()
            await self.redis.set_task_progress(task_id, progress)
            return False

    def get_supported_task_types(self) -> List[str]:
        """Get list of supported task types

        Returns:
            List of task type strings
        """
        return list(SUBTASK_DEFINITIONS.keys())

    def get_subtask_template(self, task_type: str) -> List[Dict[str, Any]]:
        """Get subtask template for a task type

        Args:
            task_type: Task type string

        Returns:
            List of subtask definitions
        """
        return SUBTASK_DEFINITIONS.get(task_type, SUBTASK_DEFINITIONS["develop_feature"])
