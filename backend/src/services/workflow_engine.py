"""
Workflow Engine

Orchestrates workflow execution with support for Sequential and Hierarchical patterns.
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowStatus, NodeStatus
from src.logging_config import get_logger

logger = get_logger(__name__)


class ExecutionMode(str, Enum):
    """Workflow execution modes."""
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    CONCURRENT = "concurrent"
    GRAPH = "graph"


class WorkflowEngine:
    """
    Main workflow execution engine.

    Supports:
    - Sequential: Linear execution, output feeds to next node
    - Hierarchical: Director agent plans and distributes to workers
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._running_workflows: Dict[str, asyncio.Task] = {}
        self._cancel_flags: Dict[str, bool] = {}

    async def start_workflow(self, workflow_id: UUID) -> Workflow:
        """Start executing a workflow."""
        workflow = await self._load_workflow(workflow_id)

        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        if workflow.status not in (WorkflowStatus.DRAFT.value, WorkflowStatus.FAILED.value, WorkflowStatus.PENDING.value):
            raise ValueError(f"Cannot start workflow with status: {workflow.status}")

        # Update workflow status
        workflow.status = WorkflowStatus.RUNNING.value
        workflow.started_at = datetime.utcnow()
        workflow.error = None
        await self.db.commit()

        # Start execution in background
        workflow_id_str = str(workflow_id)
        self._cancel_flags[workflow_id_str] = False

        task = asyncio.create_task(self._execute_workflow(workflow))
        self._running_workflows[workflow_id_str] = task

        logger.info("Workflow started", workflow_id=workflow_id_str, mode=workflow.workflow_type)

        return workflow

    async def pause_workflow(self, workflow_id: UUID) -> Workflow:
        """Pause a running workflow."""
        workflow = await self._load_workflow(workflow_id)

        if workflow.status != WorkflowStatus.RUNNING.value:
            raise ValueError("Only running workflows can be paused")

        workflow.status = WorkflowStatus.PAUSED.value
        self._cancel_flags[str(workflow_id)] = True
        await self.db.commit()

        logger.info("Workflow paused", workflow_id=str(workflow_id))
        return workflow

    async def resume_workflow(self, workflow_id: UUID) -> Workflow:
        """Resume a paused workflow."""
        workflow = await self._load_workflow(workflow_id)

        if workflow.status != WorkflowStatus.PAUSED.value:
            raise ValueError("Only paused workflows can be resumed")

        workflow.status = WorkflowStatus.RUNNING.value
        await self.db.commit()

        # Restart execution
        workflow_id_str = str(workflow_id)
        self._cancel_flags[workflow_id_str] = False

        task = asyncio.create_task(self._execute_workflow(workflow))
        self._running_workflows[workflow_id_str] = task

        logger.info("Workflow resumed", workflow_id=workflow_id_str)
        return workflow

    async def cancel_workflow(self, workflow_id: UUID) -> Workflow:
        """Cancel a workflow."""
        workflow = await self._load_workflow(workflow_id)

        if workflow.status in (WorkflowStatus.COMPLETED.value, WorkflowStatus.CANCELLED.value):
            raise ValueError(f"Cannot cancel workflow with status: {workflow.status}")

        workflow.status = WorkflowStatus.CANCELLED.value
        workflow.completed_at = datetime.utcnow()
        self._cancel_flags[str(workflow_id)] = True
        await self.db.commit()

        logger.info("Workflow cancelled", workflow_id=str(workflow_id))
        return workflow

    async def _load_workflow(self, workflow_id: UUID) -> Optional[Workflow]:
        """Load workflow with nodes and edges."""
        result = await self.db.execute(
            select(Workflow)
            .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
            .where(Workflow.workflow_id == workflow_id)
        )
        return result.scalar_one_or_none()

    async def _execute_workflow(self, workflow: Workflow):
        """Execute workflow based on its type."""
        try:
            mode = workflow.workflow_type or ExecutionMode.SEQUENTIAL.value

            if mode == ExecutionMode.SEQUENTIAL.value:
                await self._execute_sequential(workflow)
            elif mode == ExecutionMode.HIERARCHICAL.value:
                await self._execute_hierarchical(workflow)
            elif mode == ExecutionMode.CONCURRENT.value:
                await self._execute_concurrent(workflow)
            else:
                await self._execute_sequential(workflow)  # Default to sequential

            # Check if cancelled or paused
            if self._cancel_flags.get(str(workflow.workflow_id)):
                return

            # Mark as completed
            workflow.status = WorkflowStatus.COMPLETED.value
            workflow.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info("Workflow completed", workflow_id=str(workflow.workflow_id))

        except Exception as e:
            logger.error("Workflow execution failed",
                        workflow_id=str(workflow.workflow_id),
                        error=str(e))
            workflow.status = WorkflowStatus.FAILED.value
            workflow.error = str(e)
            workflow.completed_at = datetime.utcnow()
            await self.db.commit()
        finally:
            # Cleanup
            workflow_id_str = str(workflow.workflow_id)
            self._running_workflows.pop(workflow_id_str, None)
            self._cancel_flags.pop(workflow_id_str, None)

    async def _execute_sequential(self, workflow: Workflow):
        """
        Execute nodes in sequential order.
        Each node's output becomes the next node's input.
        """
        # Sort nodes by order_index
        nodes = sorted(workflow.nodes, key=lambda n: n.order_index or 0)

        previous_output: Optional[Dict[str, Any]] = workflow.context or {}

        for node in nodes:
            # Check for cancellation
            if self._cancel_flags.get(str(workflow.workflow_id)):
                logger.info("Workflow execution cancelled", workflow_id=str(workflow.workflow_id))
                return

            # Execute node
            try:
                output = await self._execute_node(node, previous_output)
                previous_output = output

                # Update progress
                workflow.completed_nodes = (workflow.completed_nodes or 0) + 1
                await self.db.commit()

            except Exception as e:
                logger.error("Node execution failed",
                           node_id=str(node.node_id),
                           error=str(e))
                node.status = NodeStatus.FAILED.value
                node.error = str(e)
                await self.db.commit()
                raise

        # Store final result
        workflow.result = previous_output

    async def _execute_hierarchical(self, workflow: Workflow):
        """
        Execute with Director-Worker pattern.

        1. Director node plans and decomposes the task
        2. Worker nodes execute in parallel or sequence
        3. Director aggregates results
        """
        nodes = workflow.nodes

        # Find director node (first node or node_type='director')
        director_node = next(
            (n for n in nodes if n.node_type == 'director'),
            nodes[0] if nodes else None
        )

        if not director_node:
            raise ValueError("Hierarchical workflow requires at least one node")

        # Get worker nodes
        worker_nodes = [n for n in nodes if n.node_id != director_node.node_id]

        # Phase 1: Director plans
        logger.info("Director planning", node_id=str(director_node.node_id))
        plan_context = workflow.context or {}
        plan_context['phase'] = 'planning'
        plan_context['worker_count'] = len(worker_nodes)

        plan_output = await self._execute_node(director_node, plan_context)

        workflow.completed_nodes = 1
        await self.db.commit()

        # Check for cancellation
        if self._cancel_flags.get(str(workflow.workflow_id)):
            return

        # Phase 2: Workers execute
        if worker_nodes:
            # Distribute tasks from plan to workers
            tasks_for_workers = plan_output.get('tasks', [])

            # Execute workers (can be parallel or sequential based on config)
            parallel = plan_output.get('parallel', False)

            if parallel:
                # Parallel execution
                worker_tasks = []
                for i, worker_node in enumerate(worker_nodes):
                    task_data = tasks_for_workers[i] if i < len(tasks_for_workers) else {}
                    worker_input = {**plan_output, 'assigned_task': task_data}
                    worker_tasks.append(self._execute_node(worker_node, worker_input))

                worker_outputs = await asyncio.gather(*worker_tasks, return_exceptions=True)

                # Handle errors
                for i, output in enumerate(worker_outputs):
                    if isinstance(output, Exception):
                        worker_nodes[i].status = NodeStatus.FAILED.value
                        worker_nodes[i].error = str(output)
                    workflow.completed_nodes = (workflow.completed_nodes or 0) + 1

            else:
                # Sequential execution
                worker_outputs = []
                for i, worker_node in enumerate(worker_nodes):
                    if self._cancel_flags.get(str(workflow.workflow_id)):
                        return

                    task_data = tasks_for_workers[i] if i < len(tasks_for_workers) else {}
                    worker_input = {**plan_output, 'assigned_task': task_data}

                    try:
                        output = await self._execute_node(worker_node, worker_input)
                        worker_outputs.append(output)
                    except Exception as e:
                        worker_outputs.append({'error': str(e)})

                    workflow.completed_nodes = (workflow.completed_nodes or 0) + 1
                    await self.db.commit()

            # Phase 3: Director aggregates
            if self._cancel_flags.get(str(workflow.workflow_id)):
                return

            logger.info("Director aggregating", node_id=str(director_node.node_id))
            aggregate_context = {
                'phase': 'aggregation',
                'plan': plan_output,
                'worker_results': worker_outputs
            }

            # Reset director for aggregation
            director_node.status = NodeStatus.PENDING.value
            final_output = await self._execute_node(director_node, aggregate_context)

            workflow.completed_nodes = (workflow.completed_nodes or 0) + 1
            workflow.result = final_output
        else:
            # No workers, just use director output
            workflow.result = plan_output

        await self.db.commit()

    async def _execute_concurrent(self, workflow: Workflow):
        """Execute all nodes concurrently."""
        nodes = workflow.nodes
        context = workflow.context or {}

        # Execute all nodes in parallel
        tasks = [self._execute_node(node, context) for node in nodes]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        results = []
        for i, output in enumerate(outputs):
            if isinstance(output, Exception):
                nodes[i].status = NodeStatus.FAILED.value
                nodes[i].error = str(output)
                results.append({'error': str(output)})
            else:
                results.append(output)
            workflow.completed_nodes = (workflow.completed_nodes or 0) + 1

        workflow.result = {'outputs': results}
        await self.db.commit()

    async def _execute_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single node.

        This is where the actual AI tool execution happens.
        For now, we'll create a task and wait for worker to execute.
        """
        node.status = NodeStatus.RUNNING.value
        node.started_at = datetime.utcnow()
        node.input_data = input_data
        await self.db.commit()

        logger.info("Executing node",
                   node_id=str(node.node_id),
                   node_type=node.node_type,
                   name=node.name)

        try:
            # Get agent config
            agent_config = node.agent_config or {}
            tool = agent_config.get('tool', 'claude_code')
            prompt = agent_config.get('prompt', '')

            # Build the full prompt with context
            full_prompt = self._build_prompt(prompt, input_data)

            # Execute via task executor (will be implemented)
            # For now, simulate execution
            output = await self._simulate_execution(node, full_prompt, agent_config)

            # Update node
            node.status = NodeStatus.COMPLETED.value
            node.completed_at = datetime.utcnow()
            node.output = output
            await self.db.commit()

            logger.info("Node completed", node_id=str(node.node_id))

            return output

        except Exception as e:
            node.status = NodeStatus.FAILED.value
            node.error = str(e)
            node.completed_at = datetime.utcnow()
            await self.db.commit()
            raise

    def _build_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """Build prompt from template and context."""
        if not template:
            return str(context)

        # Simple variable substitution
        result = template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        return result

    async def _simulate_execution(
        self,
        node: WorkflowNode,
        prompt: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate node execution.
        In production, this will dispatch to actual workers.
        """
        # Simulate processing time
        await asyncio.sleep(1)

        node_type = node.node_type

        if node_type == 'director':
            # Director returns a plan
            return {
                'plan': f"Plan for: {node.name}",
                'tasks': [
                    {'id': 1, 'description': 'Subtask 1'},
                    {'id': 2, 'description': 'Subtask 2'},
                ],
                'parallel': False,
                'prompt': prompt[:100] if prompt else ''
            }
        else:
            # Worker returns execution result
            return {
                'result': f"Executed: {node.name}",
                'status': 'success',
                'prompt': prompt[:100] if prompt else ''
            }


# Singleton engine factory
_engine_instance: Optional[WorkflowEngine] = None

def get_workflow_engine(db: AsyncSession) -> WorkflowEngine:
    """Get or create workflow engine instance."""
    return WorkflowEngine(db)
