"""
DAG Workflow Executor

Executes workflow graphs using the new DAG-based workflow system.
Integrates with the MCP Bus for tool execution and provides:
- Topological ordering for proper dependency resolution
- Parallel execution for ParallelNode branches
- Condition branching for ConditionNode
- Human review pausing for HumanReviewNode
- Loop handling for LoopNode
- Subflow execution for SubflowNode
- Dynamic routing for RouterNode
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID

from src.logging_config import get_logger
from src.mcp import get_mcp_bus, ToolResult, ToolResultStatus
from src.workflows.graph import WorkflowGraph
from src.workflows.nodes import (
    BaseNode,
    ConditionNode,
    HumanReviewNode,
    JoinNode,
    LoopNode,
    NodeStatus,
    NodeType,
    ParallelNode,
    RouterNode,
    SubflowNode,
    TaskNode,
)
from src.workflows.state import WorkflowContext, WorkflowState
from src.workflows.executor import (
    NodeExecutor,
    ExecutionContext,
    ExecutionMetrics,
    TaskExecutionError,
)

logger = get_logger(__name__)


class DAGExecutionError(Exception):
    """Base exception for DAG execution errors."""

    def __init__(self, message: str, node_id: Optional[str] = None):
        super().__init__(message)
        self.node_id = node_id


class NodeExecutionError(DAGExecutionError):
    """Raised when a node execution fails."""
    pass


class WorkflowPausedError(DAGExecutionError):
    """Raised when workflow is paused (e.g., for human review)."""
    pass


class WorkflowCancelledError(DAGExecutionError):
    """Raised when workflow execution is cancelled."""
    pass


class CycleDetectedError(DAGExecutionError):
    """Raised when a cycle is detected in the workflow graph."""
    pass


class ExecutionResult:
    """Result of a workflow execution."""

    def __init__(
        self,
        workflow_id: str,
        status: str,
        state: WorkflowState,
        error: Optional[str] = None,
        paused_at: Optional[str] = None,
    ):
        self.workflow_id = workflow_id
        self.status = status
        self.state = state
        self.error = error
        self.paused_at = paused_at
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "state": self.state.to_dict(),
            "error": self.error,
            "paused_at": self.paused_at,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class DAGExecutor:
    """
    Executes DAG-based workflows.

    Features:
    - Topological ordering for dependency resolution
    - Parallel branch execution
    - Conditional branching
    - Loop handling
    - Human review checkpoints
    - MCP Bus integration for tool execution
    - State management and persistence
    - Integration with NodeExecutor for robust node execution

    Usage:
        executor = DAGExecutor()
        result = await executor.execute(graph, context, initial_state)
    """

    def __init__(
        self,
        max_parallel_branches: int = 10,
        default_timeout: float = 300.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        node_executor: Optional[NodeExecutor] = None,
        llm_router: Optional[Callable] = None,
    ):
        """
        Initialize the DAG executor.

        Args:
            max_parallel_branches: Maximum number of parallel branches to execute
            default_timeout: Default timeout for node execution in seconds
            max_retries: Default maximum retry attempts for failed nodes
            retry_delay: Default delay between retries in seconds
            node_executor: Optional NodeExecutor instance for node execution
            llm_router: Optional LLM router callback for RouterNode decisions
        """
        self._max_parallel_branches = max_parallel_branches
        self._default_timeout = default_timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        # Node executor for individual node execution
        self._node_executor = node_executor or NodeExecutor(llm_router=llm_router)
        self._llm_router = llm_router

        # Execution tracking
        self._running_workflows: Dict[str, asyncio.Task] = {}
        self._cancel_flags: Dict[str, bool] = {}
        self._pause_flags: Dict[str, bool] = {}

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)

        # Subflow executor reference (for nested workflows)
        self._subflow_executor: Optional["DAGExecutor"] = None

        logger.info(
            "DAGExecutor initialized",
            max_parallel_branches=max_parallel_branches,
            default_timeout=default_timeout,
        )

    async def execute(
        self,
        graph: WorkflowGraph,
        context: WorkflowContext,
        initial_state: Optional[WorkflowState] = None,
    ) -> ExecutionResult:
        """
        Execute a workflow graph.

        Args:
            graph: The workflow graph to execute
            context: Workflow context with metadata
            initial_state: Optional initial state (for resuming)

        Returns:
            Execution result with final state

        Raises:
            CycleDetectedError: If graph contains cycles
            DAGExecutionError: If execution fails
        """
        workflow_id = str(context.workflow_id)

        logger.info(
            "Starting workflow execution",
            workflow_id=workflow_id,
            workflow_name=context.workflow_name,
            graph_id=graph.id,
        )

        # Validate graph
        validation_errors = graph.validate()
        if validation_errors:
            logger.error(
                "Workflow graph validation failed",
                workflow_id=workflow_id,
                errors=validation_errors,
            )
            raise DAGExecutionError(
                f"Graph validation failed: {', '.join(validation_errors)}"
            )

        # Initialize state
        state = initial_state or WorkflowState(input=context.metadata)
        state.started_at = state.started_at or datetime.utcnow()

        # Initialize tracking
        self._cancel_flags[workflow_id] = False
        self._pause_flags[workflow_id] = False

        result = ExecutionResult(
            workflow_id=workflow_id,
            status="running",
            state=state,
        )
        result.started_at = datetime.utcnow()

        try:
            # Get topological order
            execution_order = graph.topological_sort()
            logger.debug(
                "Computed execution order",
                workflow_id=workflow_id,
                order=execution_order,
            )

            # Execute the graph
            await self._execute_graph(
                graph=graph,
                state=state,
                context=context,
                execution_order=execution_order,
            )

            # Check final status
            if self._cancel_flags.get(workflow_id):
                result.status = "cancelled"
                logger.info("Workflow cancelled", workflow_id=workflow_id)
            elif self._pause_flags.get(workflow_id):
                result.status = "paused"
                result.paused_at = state.current_node
                logger.info(
                    "Workflow paused",
                    workflow_id=workflow_id,
                    paused_at=result.paused_at,
                )
            else:
                result.status = "completed"
                logger.info(
                    "Workflow completed successfully",
                    workflow_id=workflow_id,
                    completed_nodes=len(state.completed_nodes),
                )

            result.completed_at = datetime.utcnow()
            await self._emit_event(
                "workflow_completed",
                {"workflow_id": workflow_id, "status": result.status},
            )

        except WorkflowPausedError as e:
            result.status = "paused"
            result.paused_at = e.node_id
            logger.info(
                "Workflow paused for review",
                workflow_id=workflow_id,
                paused_at=e.node_id,
            )

        except WorkflowCancelledError:
            result.status = "cancelled"
            result.completed_at = datetime.utcnow()
            logger.info("Workflow execution cancelled", workflow_id=workflow_id)

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            logger.error(
                "Workflow execution failed",
                workflow_id=workflow_id,
                error=str(e),
                exc_info=True,
            )
            await self._emit_event(
                "workflow_failed",
                {"workflow_id": workflow_id, "error": str(e)},
            )

        finally:
            # Cleanup
            self._cancel_flags.pop(workflow_id, None)
            self._pause_flags.pop(workflow_id, None)

        return result

    async def _execute_graph(
        self,
        graph: WorkflowGraph,
        state: WorkflowState,
        context: WorkflowContext,
        execution_order: List[str],
    ) -> None:
        """
        Execute the workflow graph following topological order.

        Args:
            graph: Workflow graph
            state: Current workflow state
            context: Workflow context
            execution_order: Topological order of node IDs
        """
        workflow_id = str(context.workflow_id)

        # Build dependency tracking
        in_degree: Dict[str, int] = defaultdict(int)
        for node_id in graph.nodes:
            for next_id in graph.get_next_nodes(node_id):
                in_degree[next_id] += 1

        # Ready queue: nodes with all dependencies satisfied
        ready_queue: List[str] = []
        for node_id in execution_order:
            if in_degree[node_id] == 0 and node_id not in state.completed_nodes:
                ready_queue.append(node_id)

        # Active parallel branches
        active_parallel: Dict[str, Set[str]] = {}  # join_id -> active branch ids
        parallel_results: Dict[str, Dict[str, Any]] = {}  # join_id -> {branch_id: result}

        while ready_queue:
            # Check for cancellation
            if self._cancel_flags.get(workflow_id):
                raise WorkflowCancelledError("Workflow cancelled")

            # Check for pause
            if self._pause_flags.get(workflow_id):
                raise WorkflowPausedError("Workflow paused", state.current_node)

            # Get next node
            current_id = ready_queue.pop(0)

            # Skip if already completed (for resumed workflows)
            if current_id in state.completed_nodes:
                self._update_ready_queue(graph, current_id, in_degree, ready_queue, state)
                continue

            node = graph.get_node(current_id)
            if not node:
                logger.warning("Node not found in graph", node_id=current_id)
                continue

            state.current_node = current_id

            logger.info(
                "Executing node",
                workflow_id=workflow_id,
                node_id=current_id,
                node_type=node.node_type.value,
                node_name=node.name,
            )

            try:
                # Execute based on node type
                if node.node_type == NodeType.PARALLEL:
                    await self._handle_parallel_node(
                        node, graph, state, context, ready_queue,
                        active_parallel, parallel_results, in_degree
                    )
                elif node.node_type == NodeType.JOIN:
                    await self._handle_join_node(
                        node, state, active_parallel, parallel_results
                    )
                    self._update_ready_queue(graph, current_id, in_degree, ready_queue, state)
                elif node.node_type == NodeType.CONDITION:
                    next_node = await self._handle_condition_node(node, state)
                    if next_node:
                        # Skip normal flow, go to specific branch
                        self._add_to_ready_queue(next_node, ready_queue, state)
                    state.mark_completed(current_id)
                elif node.node_type == NodeType.HUMAN_REVIEW:
                    await self._handle_human_review_node(node, state, workflow_id)
                elif node.node_type == NodeType.LOOP:
                    next_node = await self._handle_loop_node(node, state)
                    if next_node:
                        self._add_to_ready_queue(next_node, ready_queue, state)
                    # Don't mark completed until loop exits
                elif node.node_type == NodeType.ROUTER:
                    next_node = await self._handle_router_node(node, state, context)
                    if next_node:
                        self._add_to_ready_queue(next_node, ready_queue, state)
                    state.mark_completed(current_id)
                elif node.node_type == NodeType.SUBFLOW:
                    await self._handle_subflow_node(node, state, context)
                    state.mark_completed(current_id)
                    self._update_ready_queue(graph, current_id, in_degree, ready_queue, state)
                elif node.node_type == NodeType.TASK:
                    output = await self._execute_task_node(node, state, context)
                    state.mark_completed(current_id, output)
                    self._update_ready_queue(graph, current_id, in_degree, ready_queue, state)
                else:
                    # Default handling for unknown types
                    output = await node.execute(state.outputs)
                    state.mark_completed(current_id, output)
                    self._update_ready_queue(graph, current_id, in_degree, ready_queue, state)

                await self._emit_event(
                    "node_completed",
                    {
                        "workflow_id": workflow_id,
                        "node_id": current_id,
                        "node_type": node.node_type.value,
                    },
                )

            except WorkflowPausedError:
                raise
            except WorkflowCancelledError:
                raise
            except Exception as e:
                await self._handle_node_error(node, state, e, ready_queue, graph, in_degree)

    def _update_ready_queue(
        self,
        graph: WorkflowGraph,
        completed_id: str,
        in_degree: Dict[str, int],
        ready_queue: List[str],
        state: WorkflowState,
    ) -> None:
        """Update ready queue after a node completes."""
        for next_id in graph.get_next_nodes(completed_id):
            in_degree[next_id] -= 1
            if in_degree[next_id] <= 0 and next_id not in state.completed_nodes:
                if next_id not in ready_queue:
                    ready_queue.append(next_id)

    def _add_to_ready_queue(
        self,
        node_id: str,
        ready_queue: List[str],
        state: WorkflowState,
    ) -> None:
        """Add a node to the ready queue if not already there."""
        if node_id not in ready_queue and node_id not in state.completed_nodes:
            ready_queue.append(node_id)

    async def _execute_task_node(
        self,
        node: TaskNode,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute a task node using NodeExecutor or direct MCP Bus.

        Args:
            node: Task node to execute
            state: Current workflow state
            context: Workflow context

        Returns:
            Task execution result
        """
        # Create execution context for NodeExecutor
        exec_context = ExecutionContext(
            workflow_id=str(context.workflow_id),
            execution_id=f"{context.workflow_id}_{node.id}",
            state=state,
            timeout=node.timeout or self._default_timeout,
            max_retries=node.max_retries,
            debug=context.debug,
            llm_router=self._llm_router,
            metadata=context.metadata,
        )

        # Use NodeExecutor if tool_path is specified
        if node.tool_path:
            try:
                result = await self._node_executor.execute_task(
                    node=node,
                    state=state,
                    context=exec_context,
                )
                return result if isinstance(result, dict) else {"result": result}

            except TaskExecutionError as e:
                raise NodeExecutionError(str(e), node_id=node.id)

        # Legacy agent config support - use direct MCP invocation
        elif node.agent_config:
            node.status = NodeStatus.RUNNING
            node.started_at = datetime.utcnow()

            # Resolve inputs from state
            resolved_inputs = node.resolve_inputs(state.outputs)
            arguments = {**node.arguments, **resolved_inputs}

            output = await self._execute_legacy_agent(
                config=node.agent_config,
                inputs=arguments,
                context=context,
            )

            node.status = NodeStatus.COMPLETED
            node.completed_at = datetime.utcnow()
            return output

        else:
            # No tool or agent configured, just pass through resolved inputs
            node.status = NodeStatus.RUNNING
            node.started_at = datetime.utcnow()

            resolved_inputs = node.resolve_inputs(state.outputs)
            arguments = {**node.arguments, **resolved_inputs}

            node.status = NodeStatus.COMPLETED
            node.completed_at = datetime.utcnow()
            return arguments

    async def _invoke_mcp_tool(
        self,
        tool_path: str,
        arguments: Dict[str, Any],
        timeout: float,
        retries: int,
    ) -> ToolResult:
        """
        Invoke an MCP tool with retry logic.

        Args:
            tool_path: MCP tool path (server.tool_name)
            arguments: Tool arguments
            timeout: Timeout in seconds
            retries: Number of retry attempts

        Returns:
            Tool execution result
        """
        bus = get_mcp_bus()
        last_error: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                logger.debug(
                    "Invoking MCP tool",
                    tool_path=tool_path,
                    attempt=attempt + 1,
                    max_attempts=retries + 1,
                )

                result = await bus.invoke_tool(
                    tool_path=tool_path,
                    arguments=arguments,
                    timeout=timeout,
                )

                if result.status == ToolResultStatus.SUCCESS:
                    return result

                # Non-success but not exception - still return
                if result.status == ToolResultStatus.TIMEOUT:
                    logger.warning(
                        "Tool invocation timed out",
                        tool_path=tool_path,
                        attempt=attempt + 1,
                    )
                    last_error = TimeoutError(f"Tool {tool_path} timed out")
                else:
                    return result

            except Exception as e:
                last_error = e
                logger.warning(
                    "Tool invocation failed",
                    tool_path=tool_path,
                    attempt=attempt + 1,
                    error=str(e),
                )

            if attempt < retries:
                await asyncio.sleep(self._retry_delay * (attempt + 1))

        # All retries exhausted
        return ToolResult(
            tool_path=tool_path,
            status=ToolResultStatus.ERROR,
            error=str(last_error) if last_error else "Unknown error",
        )

    async def _execute_legacy_agent(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute using legacy agent configuration.

        Args:
            config: Agent configuration
            inputs: Input data
            context: Workflow context

        Returns:
            Execution result
        """
        # Extract configuration
        tool = config.get("tool", "claude_code")
        prompt_template = config.get("prompt", "")

        # Build prompt from template and inputs
        prompt = self._build_prompt(prompt_template, inputs)

        # Map tool to MCP path if possible
        tool_mapping = {
            "claude_code": "claude_code.execute",
            "gemini_cli": "gemini_cli.execute",
            "ollama": "ollama.generate",
        }

        tool_path = tool_mapping.get(tool, f"{tool}.execute")

        try:
            result = await self._invoke_mcp_tool(
                tool_path=tool_path,
                arguments={"prompt": prompt, **inputs},
                timeout=self._default_timeout,
                retries=self._max_retries,
            )

            if result.status == ToolResultStatus.SUCCESS:
                return result.result if result.result else {}
            else:
                return {"error": result.error, "status": "failed"}

        except Exception as e:
            logger.error("Legacy agent execution failed", error=str(e))
            return {"error": str(e), "status": "failed"}

    def _build_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """Build prompt from template and context variables."""
        if not template:
            return str(context)

        result = template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        return result

    async def _handle_parallel_node(
        self,
        node: ParallelNode,
        graph: WorkflowGraph,
        state: WorkflowState,
        context: WorkflowContext,
        ready_queue: List[str],
        active_parallel: Dict[str, Set[str]],
        parallel_results: Dict[str, Dict[str, Any]],
        in_degree: Dict[str, int],
    ) -> None:
        """
        Handle parallel node execution.

        Spawns all branches concurrently and waits for completion.
        """
        workflow_id = str(context.workflow_id)
        branch_ids = node.branches

        if not branch_ids:
            logger.warning("Parallel node has no branches", node_id=node.id)
            state.mark_completed(node.id)
            return

        logger.info(
            "Starting parallel execution",
            workflow_id=workflow_id,
            node_id=node.id,
            branches=branch_ids,
        )

        # Find the corresponding join node
        join_node_id = self._find_join_node(graph, node.id, branch_ids)

        # Track parallel branches
        state.start_parallel(join_node_id or node.id, branch_ids)
        active_parallel[join_node_id or node.id] = set(branch_ids)
        parallel_results[join_node_id or node.id] = {}

        # Execute branches concurrently
        async def execute_branch(branch_id: str) -> Tuple[str, Any]:
            """Execute a single parallel branch."""
            branch_node = graph.get_node(branch_id)
            if not branch_node:
                return branch_id, {"error": f"Branch node not found: {branch_id}"}

            try:
                if branch_node.node_type == NodeType.TASK:
                    result = await self._execute_task_node(branch_node, state, context)
                else:
                    result = await branch_node.execute(state.outputs)

                state.mark_completed(branch_id, result)
                return branch_id, result

            except Exception as e:
                logger.error(
                    "Parallel branch failed",
                    branch_id=branch_id,
                    error=str(e),
                )
                state.mark_failed(branch_id, str(e))

                if node.fail_fast:
                    raise

                return branch_id, {"error": str(e)}

        # Limit concurrent branches
        semaphore = asyncio.Semaphore(self._max_parallel_branches)

        async def limited_execute(branch_id: str) -> Tuple[str, Any]:
            async with semaphore:
                return await execute_branch(branch_id)

        # Execute all branches
        tasks = [limited_execute(bid) for bid in branch_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(results):
            branch_id = branch_ids[i]
            if isinstance(result, Exception):
                parallel_results[join_node_id or node.id][branch_id] = {
                    "error": str(result)
                }
                if node.fail_fast:
                    raise result
            else:
                branch_id_result, branch_output = result
                parallel_results[join_node_id or node.id][branch_id_result] = branch_output
                state.complete_branch(join_node_id or node.id, branch_id_result, branch_output)

        state.mark_completed(node.id)

        # Add join node to ready queue if all branches complete
        if join_node_id:
            self._add_to_ready_queue(join_node_id, ready_queue, state)

    def _find_join_node(
        self,
        graph: WorkflowGraph,
        parallel_id: str,
        branch_ids: List[str],
    ) -> Optional[str]:
        """Find the join node for a parallel split."""
        # Find common successor of all branches
        if not branch_ids:
            return None

        # Get successors of first branch
        first_successors = set(graph.get_next_nodes(branch_ids[0]))

        # Find intersection with all other branches
        common = first_successors
        for branch_id in branch_ids[1:]:
            branch_successors = set(graph.get_next_nodes(branch_id))
            common = common.intersection(branch_successors)

        # Look for JoinNode in common successors
        for node_id in common:
            node = graph.get_node(node_id)
            if node and node.node_type == NodeType.JOIN:
                return node_id

        # Return first common successor if no explicit join
        return next(iter(common), None)

    async def _handle_join_node(
        self,
        node: JoinNode,
        state: WorkflowState,
        active_parallel: Dict[str, Set[str]],
        parallel_results: Dict[str, Dict[str, Any]],
    ) -> None:
        """Handle join node - merge parallel results."""
        join_id = node.id

        # Get results from parallel execution
        results = parallel_results.get(join_id, state.get_parallel_results(join_id))

        # Store merged results based on merge strategy
        state.outputs["_parallel_results"] = results

        merged_output = await node.execute(state.outputs)
        state.outputs.pop("_parallel_results", None)

        # Store merged result
        state.mark_completed(join_id, merged_output)

        # Cleanup tracking
        active_parallel.pop(join_id, None)
        parallel_results.pop(join_id, None)

        logger.info(
            "Join node completed",
            node_id=join_id,
            merge_strategy=node.merge_strategy,
            branch_count=len(results),
        )

    async def _handle_condition_node(
        self,
        node: ConditionNode,
        state: WorkflowState,
    ) -> Optional[str]:
        """
        Handle condition node - evaluate and return target branch.

        Returns:
            Node ID of the branch to execute
        """
        result = await node.execute(state.outputs)
        branch = result.get("branch")
        condition_result = result.get("condition_result")

        logger.info(
            "Condition evaluated",
            node_id=node.id,
            result=condition_result,
            branch=branch,
        )

        state.outputs[node.output_key] = result
        return branch

    async def _handle_human_review_node(
        self,
        node: HumanReviewNode,
        state: WorkflowState,
        workflow_id: str,
    ) -> None:
        """
        Handle human review node - pause workflow for approval.

        Raises:
            WorkflowPausedError: Always, to pause the workflow
        """
        node.status = NodeStatus.WAITING

        # Add to pending reviews
        state.add_pending_review(node.id)

        # Store review request in state
        state.outputs[node.id] = {
            "waiting_for_review": True,
            "review_type": node.review_type,
            "instructions": node.instructions,
            "required_fields": node.required_fields,
            "urgency": node.urgency,
            "timeout_hours": node.timeout_hours,
            "approve_branch": node.approve_branch,
            "reject_branch": node.reject_branch,
        }

        await self._emit_event(
            "human_review_required",
            {
                "workflow_id": workflow_id,
                "node_id": node.id,
                "review_type": node.review_type,
                "instructions": node.instructions,
                "urgency": node.urgency,
            },
        )

        logger.info(
            "Workflow paused for human review",
            workflow_id=workflow_id,
            node_id=node.id,
            review_type=node.review_type,
        )

        raise WorkflowPausedError(
            f"Waiting for human review: {node.instructions}",
            node_id=node.id,
        )

    async def resume_after_review(
        self,
        graph: WorkflowGraph,
        context: WorkflowContext,
        state: WorkflowState,
        review_node_id: str,
        decision: str,
        review_data: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Resume workflow after human review.

        Args:
            graph: Workflow graph
            context: Workflow context
            state: Current workflow state
            review_node_id: ID of the review node
            decision: Review decision ("approve" or "reject")
            review_data: Optional additional data from reviewer

        Returns:
            Execution result after resumption
        """
        node = graph.get_node(review_node_id)
        if not node or node.node_type != NodeType.HUMAN_REVIEW:
            raise DAGExecutionError(f"Invalid review node: {review_node_id}")

        human_node: HumanReviewNode = node  # type: ignore

        # Complete the review
        state.complete_review(review_node_id)
        human_node.status = NodeStatus.COMPLETED

        # Store review result
        state.outputs[f"{review_node_id}_review"] = {
            "decision": decision,
            "data": review_data,
            "reviewed_at": datetime.utcnow().isoformat(),
        }

        state.mark_completed(review_node_id)

        # Determine next node based on decision
        if decision == "approve":
            next_node = human_node.approve_branch
        else:
            next_node = human_node.reject_branch

        # Update state for continuation
        if next_node:
            state.current_node = next_node

        logger.info(
            "Resuming workflow after review",
            workflow_id=str(context.workflow_id),
            review_node_id=review_node_id,
            decision=decision,
            next_node=next_node,
        )

        # Continue execution
        return await self.execute(graph, context, state)

    async def _handle_loop_node(
        self,
        node: LoopNode,
        state: WorkflowState,
    ) -> Optional[str]:
        """
        Handle loop node - evaluate condition and return next node.

        Returns:
            Next node ID (body or after_loop)
        """
        # Increment iteration counter
        iteration = state.increment_loop(node.id)
        node.current_iteration = iteration

        result = await node.execute(state.outputs)
        action = result.get("loop_action")
        next_node = result.get("next_node")

        logger.info(
            "Loop iteration",
            node_id=node.id,
            iteration=iteration,
            action=action,
            next_node=next_node,
        )

        if action == "exit":
            # Loop complete
            state.reset_loop(node.id)
            state.mark_completed(node.id, result)

        state.outputs[f"{node.id}_loop"] = result
        return next_node

    async def _handle_router_node(
        self,
        node: RouterNode,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Optional[str]:
        """
        Handle router node - use LLM to determine routing via NodeExecutor.

        Returns:
            Node ID of selected route
        """
        # Create execution context for NodeExecutor
        exec_context = ExecutionContext(
            workflow_id=str(context.workflow_id),
            execution_id=f"{context.workflow_id}_{node.id}",
            state=state,
            timeout=30.0,
            max_retries=2,
            debug=context.debug,
            llm_router=self._llm_router,
            metadata=context.metadata,
        )

        try:
            # Use NodeExecutor to handle routing
            next_node = await self._node_executor.execute_router(
                node=node,
                state=state,
                context=exec_context,
            )

            logger.info(
                "Router selected route",
                node_id=node.id,
                next_node=next_node,
            )

            return next_node

        except Exception as e:
            logger.warning(
                "Router execution failed, using default",
                node_id=node.id,
                error=str(e),
            )

            # Fall back to default route
            if node.default_route:
                state.outputs[node.output_key] = {
                    "selected_route": "default",
                    "target_node": node.default_route,
                }
                return node.default_route

            return None

    async def _handle_subflow_node(
        self,
        node: SubflowNode,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> None:
        """Handle subflow node - execute nested workflow."""
        logger.info(
            "Starting subflow execution",
            parent_node=node.id,
            workflow_id=str(node.workflow_id) if node.workflow_id else node.workflow_template,
        )

        # Build subflow inputs
        subflow_inputs = {}
        for state_key, input_key in node.subflow_inputs.items():
            if state_key in state.outputs:
                subflow_inputs[input_key] = state.outputs[state_key]

        if node.inherit_state:
            subflow_inputs = {**state.outputs, **subflow_inputs}

        # TODO: Load subflow graph from database or template registry
        # For now, this is a placeholder that needs integration with workflow storage
        logger.warning(
            "Subflow execution requires workflow loading implementation",
            workflow_id=str(node.workflow_id),
        )

        # Placeholder result
        subflow_result = {
            "status": "skipped",
            "reason": "Subflow loading not implemented",
            "workflow_id": str(node.workflow_id) if node.workflow_id else None,
        }

        # Map subflow outputs back to parent state
        for subflow_key, state_key in node.subflow_outputs.items():
            if subflow_key in subflow_result:
                state.outputs[state_key] = subflow_result[subflow_key]

        state.outputs[node.output_key] = subflow_result

    async def _handle_node_error(
        self,
        node: BaseNode,
        state: WorkflowState,
        error: Exception,
        ready_queue: List[str],
        graph: WorkflowGraph,
        in_degree: Dict[str, int],
    ) -> None:
        """Handle node execution error with retry logic."""
        node.retry_count += 1
        node.error = str(error)

        if node.retry_count <= node.max_retries:
            logger.warning(
                "Node execution failed, retrying",
                node_id=node.id,
                retry_count=node.retry_count,
                max_retries=node.max_retries,
                error=str(error),
            )

            # Wait before retry
            await asyncio.sleep(node.retry_delay * node.retry_count)

            # Re-add to ready queue for retry
            self._add_to_ready_queue(node.id, ready_queue, state)

        else:
            # Max retries exceeded
            node.status = NodeStatus.FAILED
            state.mark_failed(node.id, str(error))

            logger.error(
                "Node execution failed after max retries",
                node_id=node.id,
                error=str(error),
            )

            raise NodeExecutionError(str(error), node_id=node.id)

    def cancel(self, workflow_id: str) -> bool:
        """
        Cancel a running workflow.

        Args:
            workflow_id: Workflow ID to cancel

        Returns:
            True if cancellation was requested
        """
        if workflow_id in self._cancel_flags:
            self._cancel_flags[workflow_id] = True
            logger.info("Workflow cancellation requested", workflow_id=workflow_id)
            return True
        return False

    def pause(self, workflow_id: str) -> bool:
        """
        Pause a running workflow.

        Args:
            workflow_id: Workflow ID to pause

        Returns:
            True if pause was requested
        """
        if workflow_id in self._pause_flags:
            self._pause_flags[workflow_id] = True
            logger.info("Workflow pause requested", workflow_id=workflow_id)
            return True
        return False

    def on_event(self, event: str, handler: Callable) -> None:
        """
        Register an event handler.

        Args:
            event: Event name (e.g., "node_completed", "workflow_failed")
            handler: Async handler function
        """
        self._event_handlers[event].append(handler)

    def off_event(self, event: str, handler: Callable) -> None:
        """
        Unregister an event handler.

        Args:
            event: Event name
            handler: Handler to remove
        """
        if handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)

    async def _emit_event(self, event: str, data: Dict[str, Any]) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, data)
                else:
                    handler(event, data)
            except Exception as e:
                logger.error(
                    "Error in event handler",
                    event=event,
                    error=str(e),
                )


# Singleton instance
_executor_instance: Optional[DAGExecutor] = None


def get_dag_executor() -> DAGExecutor:
    """Get or create the singleton DAG executor instance."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = DAGExecutor()
    return _executor_instance


async def create_dag_executor(
    max_parallel_branches: int = 10,
    default_timeout: float = 300.0,
    max_retries: int = 3,
) -> DAGExecutor:
    """
    Create a new DAG executor with custom configuration.

    Args:
        max_parallel_branches: Maximum parallel branches
        default_timeout: Default node timeout
        max_retries: Default retry count

    Returns:
        Configured DAG executor
    """
    return DAGExecutor(
        max_parallel_branches=max_parallel_branches,
        default_timeout=default_timeout,
        max_retries=max_retries,
    )
