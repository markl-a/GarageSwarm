"""
Workflow Node Executor

Executes workflow nodes using the MCP Bus for tool invocations.
Handles task execution, condition evaluation, router decisions, and loop control.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from src.mcp import get_mcp_bus, ToolResult, ToolResultStatus

from .nodes import (
    BaseNode,
    ConditionNode,
    LoopNode,
    NodeStatus,
    RouterNode,
    TaskNode,
)
from .state import WorkflowState


logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Metrics for node execution."""
    node_id: str
    node_type: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_time: float = 0.0
    retry_count: int = 0
    status: str = "pending"
    error: Optional[str] = None
    tool_invocations: int = 0

    def complete(self, status: str = "completed", error: Optional[str] = None) -> None:
        """Mark execution as complete."""
        self.completed_at = datetime.utcnow()
        self.execution_time = (self.completed_at - self.started_at).total_seconds()
        self.status = status
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time": self.execution_time,
            "retry_count": self.retry_count,
            "status": self.status,
            "error": self.error,
            "tool_invocations": self.tool_invocations,
        }


@dataclass
class ExecutionContext:
    """Context for node execution."""
    workflow_id: str
    execution_id: str
    state: WorkflowState
    timeout: float = 60.0
    max_retries: int = 3
    debug: bool = False
    llm_router: Optional[Callable] = None  # Callback for LLM routing decisions
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Metrics tracking
    metrics: Dict[str, ExecutionMetrics] = field(default_factory=dict)

    def get_metrics(self, node_id: str) -> Optional[ExecutionMetrics]:
        """Get metrics for a node."""
        return self.metrics.get(node_id)

    def all_metrics(self) -> List[Dict[str, Any]]:
        """Get all metrics as list of dicts."""
        return [m.to_dict() for m in self.metrics.values()]


class ExecutorError(Exception):
    """Base exception for executor errors."""
    pass


class TaskExecutionError(ExecutorError):
    """Error during task execution."""
    pass


class ConditionEvaluationError(ExecutorError):
    """Error during condition evaluation."""
    pass


class RouterDecisionError(ExecutorError):
    """Error during router decision."""
    pass


class TimeoutError(ExecutorError):
    """Execution timed out."""
    pass


class NodeExecutor:
    """
    Executor for workflow nodes.

    Handles execution of different node types using the MCP Bus
    for tool invocations. Provides retry logic, timeout handling,
    and execution metrics tracking.
    """

    def __init__(self, llm_router: Optional[Callable] = None):
        """
        Initialize the node executor.

        Args:
            llm_router: Optional callback for LLM-based routing decisions.
                        Signature: async def router(prompt: str, routes: Dict[str, str], state: Dict) -> str
        """
        self._bus = get_mcp_bus()
        self._llm_router = llm_router
        logger.info("NodeExecutor initialized")

    async def execute_task(
        self,
        node: TaskNode,
        state: WorkflowState,
        context: Optional[ExecutionContext] = None
    ) -> Any:
        """
        Execute a TaskNode by invoking an MCP tool.

        Args:
            node: The TaskNode to execute
            state: Current workflow state
            context: Optional execution context

        Returns:
            Tool execution result

        Raises:
            TaskExecutionError: If execution fails after all retries
            TimeoutError: If execution times out
        """
        metrics = ExecutionMetrics(
            node_id=node.id,
            node_type="task"
        )

        if context:
            context.metrics[node.id] = metrics

        logger.info(f"Executing task node: {node.name} (tool: {node.tool_path})")

        # Resolve input arguments from state
        resolved_inputs = node.resolve_inputs(state.to_dict())

        # Merge static arguments with resolved inputs
        arguments = {**node.arguments, **resolved_inputs}

        # Determine timeout
        timeout = node.timeout
        if context and context.timeout:
            timeout = min(timeout, context.timeout)

        # Determine max retries
        max_retries = node.max_retries
        if context:
            max_retries = min(max_retries, context.max_retries)

        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            metrics.retry_count = attempt

            try:
                logger.debug(
                    f"Task {node.name} attempt {attempt + 1}/{max_retries + 1} "
                    f"with arguments: {arguments}"
                )

                # Invoke tool via MCP Bus with timeout
                result = await asyncio.wait_for(
                    self._bus.invoke_tool(
                        tool_path=node.tool_path,
                        arguments=arguments,
                        timeout=timeout
                    ),
                    timeout=timeout
                )

                metrics.tool_invocations += 1

                # Check result status
                if isinstance(result, ToolResult):
                    if result.status == ToolResultStatus.SUCCESS:
                        metrics.complete("completed")

                        # Store result in state
                        output_value = result.result
                        state.update(node.output_key, output_value)
                        state.mark_completed(node.id, output_value)

                        logger.info(
                            f"Task {node.name} completed successfully "
                            f"(time: {metrics.execution_time:.2f}s)"
                        )

                        return output_value

                    elif result.status == ToolResultStatus.TIMEOUT:
                        raise asyncio.TimeoutError(
                            f"Tool execution timed out: {result.error}"
                        )

                    else:
                        raise TaskExecutionError(
                            f"Tool execution failed: {result.error}"
                        )
                else:
                    # Direct result (shouldn't happen with proper ToolResult)
                    metrics.complete("completed")
                    state.update(node.output_key, result)
                    state.mark_completed(node.id, result)
                    return result

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"Task {node.name} timed out on attempt {attempt + 1}"
                )

                if attempt < max_retries:
                    # Exponential backoff
                    delay = node.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)

            except Exception as e:
                last_error = e
                logger.error(
                    f"Task {node.name} failed on attempt {attempt + 1}: {e}"
                )

                if attempt < max_retries:
                    delay = node.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)

        # All retries exhausted
        error_msg = str(last_error) if last_error else "Unknown error"
        metrics.complete("failed", error_msg)
        state.mark_failed(node.id, error_msg)

        if isinstance(last_error, asyncio.TimeoutError):
            raise TimeoutError(
                f"Task {node.name} timed out after {max_retries + 1} attempts: {error_msg}"
            )

        raise TaskExecutionError(
            f"Task {node.name} failed after {max_retries + 1} attempts: {error_msg}"
        )

    async def execute_condition(
        self,
        node: ConditionNode,
        state: WorkflowState,
        context: Optional[ExecutionContext] = None
    ) -> str:
        """
        Execute a ConditionNode by evaluating conditions.

        Args:
            node: The ConditionNode to execute
            state: Current workflow state
            context: Optional execution context

        Returns:
            Node ID of the next node (true_branch or false_branch)

        Raises:
            ConditionEvaluationError: If evaluation fails
        """
        metrics = ExecutionMetrics(
            node_id=node.id,
            node_type="condition"
        )

        if context:
            context.metrics[node.id] = metrics

        logger.info(f"Evaluating condition node: {node.name}")

        try:
            # Build state dictionary for evaluation
            state_dict = {
                **state.input,
                **state.outputs
            }

            # Evaluate conditions
            result = node.evaluate(state_dict)

            # Determine next node
            next_node = node.true_branch if result else node.false_branch

            metrics.complete("completed")
            state.mark_completed(node.id, {
                "condition_result": result,
                "next_node": next_node
            })

            logger.info(
                f"Condition {node.name} evaluated to {result}, "
                f"next node: {next_node}"
            )

            return next_node

        except Exception as e:
            error_msg = f"Condition evaluation failed: {e}"
            metrics.complete("failed", error_msg)
            state.mark_failed(node.id, error_msg)

            logger.error(f"Condition {node.name} evaluation failed: {e}")
            raise ConditionEvaluationError(error_msg)

    async def execute_router(
        self,
        node: RouterNode,
        state: WorkflowState,
        context: Optional[ExecutionContext] = None
    ) -> str:
        """
        Execute a RouterNode by using LLM to decide routing.

        Args:
            node: The RouterNode to execute
            state: Current workflow state
            context: Optional execution context

        Returns:
            Node ID of the selected route

        Raises:
            RouterDecisionError: If routing decision fails
        """
        metrics = ExecutionMetrics(
            node_id=node.id,
            node_type="router"
        )

        if context:
            context.metrics[node.id] = metrics

        logger.info(f"Executing router node: {node.name}")

        try:
            # Build state dictionary for routing
            state_dict = {
                **state.input,
                **state.outputs
            }

            # Get LLM router callback
            llm_router = self._llm_router
            if context and context.llm_router:
                llm_router = context.llm_router

            if llm_router:
                # Use LLM to decide route
                route_label = await self._llm_route_decision(
                    node=node,
                    state_dict=state_dict,
                    llm_router=llm_router
                )
            else:
                # Fallback: use MCP tool for routing
                route_label = await self._mcp_route_decision(
                    node=node,
                    state_dict=state_dict
                )

            # Get node ID for the selected route
            if route_label in node.routes:
                next_node = node.routes[route_label]
            elif node.default_route:
                logger.warning(
                    f"Router {node.name}: route '{route_label}' not found, "
                    f"using default: {node.default_route}"
                )
                next_node = node.default_route
            else:
                raise RouterDecisionError(
                    f"Invalid route '{route_label}' and no default route configured"
                )

            metrics.complete("completed")
            state.mark_completed(node.id, {
                "selected_route": route_label,
                "next_node": next_node
            })

            logger.info(
                f"Router {node.name} selected route '{route_label}', "
                f"next node: {next_node}"
            )

            return next_node

        except RouterDecisionError:
            raise
        except Exception as e:
            error_msg = f"Router decision failed: {e}"
            metrics.complete("failed", error_msg)
            state.mark_failed(node.id, error_msg)

            logger.error(f"Router {node.name} failed: {e}")
            raise RouterDecisionError(error_msg)

    async def _llm_route_decision(
        self,
        node: RouterNode,
        state_dict: Dict[str, Any],
        llm_router: Callable
    ) -> str:
        """
        Make routing decision using LLM callback.

        Args:
            node: Router node
            state_dict: Current state as dictionary
            llm_router: LLM router callback

        Returns:
            Selected route label
        """
        # Build prompt with state context
        prompt = node.routing_prompt

        # Format state for prompt if needed
        if "{state}" in prompt:
            import json
            state_json = json.dumps(state_dict, indent=2, default=str)
            prompt = prompt.replace("{state}", state_json)

        # Call LLM router
        if asyncio.iscoroutinefunction(llm_router):
            route_label = await llm_router(prompt, node.routes, state_dict)
        else:
            route_label = llm_router(prompt, node.routes, state_dict)

        return str(route_label).strip()

    async def _mcp_route_decision(
        self,
        node: RouterNode,
        state_dict: Dict[str, Any]
    ) -> str:
        """
        Make routing decision using MCP tool.

        Args:
            node: Router node
            state_dict: Current state as dictionary

        Returns:
            Selected route label
        """
        import json

        # Build routing prompt
        route_options = list(node.routes.keys())

        prompt = f"""Based on the following workflow state, select the best route.

Routing Instruction: {node.routing_prompt}

Available routes: {route_options}

Current state:
{json.dumps(state_dict, indent=2, default=str)}

Respond with ONLY the route name, nothing else."""

        # Use the configured model for routing
        tool_path = f"{node.model}.generate"

        try:
            result = await self._bus.invoke_tool(
                tool_path=tool_path,
                arguments={"prompt": prompt}
            )

            if isinstance(result, ToolResult) and result.status == ToolResultStatus.SUCCESS:
                # Extract route from result
                response = str(result.result)

                # Try to find matching route
                for route in route_options:
                    if route.lower() in response.lower():
                        return route

                # Return as-is and let caller handle validation
                return response.strip()
            else:
                error = result.error if isinstance(result, ToolResult) else "Unknown error"
                raise RouterDecisionError(f"LLM routing failed: {error}")

        except Exception as e:
            logger.warning(f"MCP routing failed, using default route: {e}")
            if node.default_route:
                return list(node.routes.keys())[0] if node.routes else ""
            raise

    async def execute_loop(
        self,
        node: LoopNode,
        state: WorkflowState,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """
        Execute a LoopNode by evaluating loop condition.

        Args:
            node: The LoopNode to execute
            state: Current workflow state
            context: Optional execution context

        Returns:
            Dictionary with loop action and next node:
            - {"loop_action": "continue", "next_node": body_node, "iteration": n}
            - {"loop_action": "exit", "next_node": after_loop, "reason": "..."}
        """
        metrics = ExecutionMetrics(
            node_id=node.id,
            node_type="loop"
        )

        if context:
            context.metrics[node.id] = metrics

        logger.info(f"Evaluating loop node: {node.name}")

        try:
            # Increment iteration counter in state
            iteration = state.increment_loop(node.id)

            # Update node's iteration tracker
            node.current_iteration = iteration

            # Build state dictionary for evaluation
            state_dict = {
                **state.input,
                **state.outputs,
                "_loop_iteration": iteration,
                "_break_loop": state.outputs.get("_break_loop", False)
            }

            # Execute the loop node (it handles condition evaluation)
            result = await node.execute(state_dict)

            metrics.complete("completed")
            state.mark_completed(node.id, result)

            if result["loop_action"] == "exit":
                # Reset loop counter when exiting
                state.reset_loop(node.id)
                logger.info(
                    f"Loop {node.name} exiting after {iteration} iterations "
                    f"(reason: {result.get('reason', 'unknown')})"
                )
            else:
                logger.info(
                    f"Loop {node.name} continuing iteration {iteration}"
                )

            return result

        except Exception as e:
            error_msg = f"Loop evaluation failed: {e}"
            metrics.complete("failed", error_msg)
            state.mark_failed(node.id, error_msg)

            logger.error(f"Loop {node.name} failed: {e}")

            # Return exit action on error
            return {
                "loop_action": "exit",
                "next_node": node.after_loop,
                "reason": "error",
                "error": error_msg
            }

    async def execute_node(
        self,
        node: BaseNode,
        state: WorkflowState,
        context: Optional[ExecutionContext] = None
    ) -> Any:
        """
        Execute any node type.

        Dispatches to the appropriate executor method based on node type.

        Args:
            node: The node to execute
            state: Current workflow state
            context: Optional execution context

        Returns:
            Node execution result (varies by node type)

        Raises:
            ExecutorError: If execution fails
        """
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.utcnow()

        try:
            if isinstance(node, TaskNode):
                result = await self.execute_task(node, state, context)
            elif isinstance(node, ConditionNode):
                result = await self.execute_condition(node, state, context)
            elif isinstance(node, RouterNode):
                result = await self.execute_router(node, state, context)
            elif isinstance(node, LoopNode):
                result = await self.execute_loop(node, state, context)
            else:
                # For other node types, use default execute
                state_dict = {**state.input, **state.outputs}
                result = await node.execute(state_dict)
                state.mark_completed(node.id, result)

            node.status = NodeStatus.COMPLETED
            node.completed_at = datetime.utcnow()

            return result

        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = str(e)
            node.completed_at = datetime.utcnow()
            raise

    def get_execution_summary(
        self,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Get execution summary from context.

        Args:
            context: Execution context with metrics

        Returns:
            Summary dictionary with execution statistics
        """
        metrics = context.all_metrics()

        total_time = sum(m["execution_time"] for m in metrics)
        completed = sum(1 for m in metrics if m["status"] == "completed")
        failed = sum(1 for m in metrics if m["status"] == "failed")
        total_retries = sum(m["retry_count"] for m in metrics)
        total_invocations = sum(m["tool_invocations"] for m in metrics)

        return {
            "workflow_id": context.workflow_id,
            "execution_id": context.execution_id,
            "total_nodes": len(metrics),
            "completed_nodes": completed,
            "failed_nodes": failed,
            "total_execution_time": total_time,
            "total_retries": total_retries,
            "total_tool_invocations": total_invocations,
            "node_metrics": metrics
        }
