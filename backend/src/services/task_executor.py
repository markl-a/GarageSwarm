"""
Task Executor Service

Handles actual task execution via Workers (CLI or API).
Supports multiple AI tools: Claude Code, Gemini CLI, etc.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.worker import Worker
from src.models.task import Task, TaskStatus
from src.logging_config import get_logger

logger = get_logger(__name__)


class ExecutionMethod(str, Enum):
    """How to execute the task."""
    WORKER_CLI = "worker_cli"      # Worker executes via CLI (claude, gemini)
    WORKER_API = "worker_api"      # Worker executes via API
    DIRECT_API = "direct_api"      # Backend directly calls API


class ToolType(str, Enum):
    """Supported AI tools."""
    CLAUDE_CODE = "claude_code"
    GEMINI_CLI = "gemini_cli"
    OLLAMA = "ollama"
    ANTHROPIC_API = "anthropic_api"
    GOOGLE_API = "google_api"


class TaskExecutor:
    """
    Executes tasks via Workers or direct API calls.

    Execution flow:
    1. Find available worker with required tool
    2. Send task to worker (push) or queue for pull
    3. Wait for result with timeout
    4. Handle retries on failure
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._pending_results: Dict[str, asyncio.Event] = {}
        self._results: Dict[str, Dict[str, Any]] = {}

    async def execute(
        self,
        prompt: str,
        tool: str = ToolType.CLAUDE_CODE.value,
        config: Optional[Dict[str, Any]] = None,
        timeout: int = 300,
        retry_count: int = 3,
        workflow_node_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task and return the result.

        Args:
            prompt: The task prompt/instructions
            tool: Which AI tool to use
            config: Additional configuration
            timeout: Execution timeout in seconds
            retry_count: Number of retries on failure

        Returns:
            Execution result dictionary
        """
        config = config or {}
        execution_id = str(uuid4())

        logger.info("Executing task",
                   execution_id=execution_id,
                   tool=tool,
                   prompt_length=len(prompt))

        for attempt in range(retry_count):
            try:
                # Find available worker
                worker = await self._find_worker(tool)

                if worker:
                    # Execute via worker
                    result = await self._execute_via_worker(
                        worker=worker,
                        prompt=prompt,
                        tool=tool,
                        config=config,
                        timeout=timeout,
                        execution_id=execution_id,
                    )
                else:
                    # Fallback to direct API
                    logger.warning("No worker available, using direct API",
                                 tool=tool)
                    result = await self._execute_direct_api(
                        prompt=prompt,
                        tool=tool,
                        config=config,
                        timeout=timeout,
                    )

                logger.info("Task executed successfully",
                          execution_id=execution_id,
                          attempt=attempt + 1)

                return result

            except asyncio.TimeoutError:
                logger.warning("Task execution timeout",
                             execution_id=execution_id,
                             attempt=attempt + 1)
                if attempt == retry_count - 1:
                    raise

            except Exception as e:
                logger.error("Task execution failed",
                           execution_id=execution_id,
                           attempt=attempt + 1,
                           error=str(e))
                if attempt == retry_count - 1:
                    raise

                # Wait before retry
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Task execution failed after all retries")

    async def _find_worker(self, tool: str) -> Optional[Worker]:
        """Find an available worker that supports the required tool."""
        result = await self.db.execute(
            select(Worker)
            .where(
                Worker.status.in_(['online', 'idle']),
                Worker.tools.contains([tool])
            )
            .order_by(Worker.last_heartbeat.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _execute_via_worker(
        self,
        worker: Worker,
        prompt: str,
        tool: str,
        config: Dict[str, Any],
        timeout: int,
        execution_id: str,
    ) -> Dict[str, Any]:
        """Execute task via a worker agent."""
        # Create task record
        task = Task(
            description=prompt[:500],  # Truncate for storage
            status=TaskStatus.PENDING.value,
            tool_preferences=[tool],
            task_metadata={
                'execution_id': execution_id,
                'full_prompt': prompt,
                'config': config,
            }
        )
        self.db.add(task)
        await self.db.flush()

        # Set up result waiting
        event = asyncio.Event()
        self._pending_results[execution_id] = event

        try:
            # Send task to worker via WebSocket (or queue for pull)
            await self._dispatch_to_worker(worker, task, prompt, tool, config)

            # Wait for result with timeout
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                task.status = TaskStatus.FAILED.value
                await self.db.commit()
                raise

            # Get result
            result = self._results.pop(execution_id, {})

            # Update task
            if result.get('success'):
                task.status = TaskStatus.COMPLETED.value
            else:
                task.status = TaskStatus.FAILED.value

            task.completed_at = datetime.utcnow()
            await self.db.commit()

            return result

        finally:
            self._pending_results.pop(execution_id, None)

    async def _dispatch_to_worker(
        self,
        worker: Worker,
        task: Task,
        prompt: str,
        tool: str,
        config: Dict[str, Any],
    ):
        """Send task to worker for execution."""
        # Update worker status
        worker.status = 'busy'
        worker.current_task_id = task.task_id
        await self.db.commit()

        # In production, send via WebSocket
        # For now, we'll simulate by updating task status
        task.status = TaskStatus.IN_PROGRESS.value
        task.started_at = datetime.utcnow()
        await self.db.commit()

        logger.info("Task dispatched to worker",
                   task_id=str(task.task_id),
                   worker_id=str(worker.worker_id))

    async def _execute_direct_api(
        self,
        prompt: str,
        tool: str,
        config: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """Execute task directly via API (fallback)."""
        if tool in [ToolType.CLAUDE_CODE.value, ToolType.ANTHROPIC_API.value]:
            return await self._call_anthropic_api(prompt, config, timeout)
        elif tool in [ToolType.GEMINI_CLI.value, ToolType.GOOGLE_API.value]:
            return await self._call_google_api(prompt, config, timeout)
        elif tool == ToolType.OLLAMA.value:
            return await self._call_ollama(prompt, config, timeout)
        else:
            raise ValueError(f"Unsupported tool: {tool}")

    async def _call_anthropic_api(
        self,
        prompt: str,
        config: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """Call Anthropic Claude API directly."""
        try:
            import anthropic
            from src.config import settings

            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not configured")

            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

            model = config.get('model', 'claude-sonnet-4-20250514')
            max_tokens = config.get('max_tokens', 4096)

            response = await asyncio.wait_for(
                client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                ),
                timeout=timeout
            )

            return {
                'success': True,
                'output': response.content[0].text,
                'model': model,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                }
            }

        except ImportError:
            logger.warning("anthropic package not installed")
            return await self._simulate_response(prompt)
        except Exception as e:
            logger.error("Anthropic API error", error=str(e))
            return {'success': False, 'error': str(e)}

    async def _call_google_api(
        self,
        prompt: str,
        config: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """Call Google Gemini API directly."""
        try:
            import google.generativeai as genai
            from src.config import settings

            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY not configured")

            genai.configure(api_key=settings.GOOGLE_API_KEY)

            model_name = config.get('model', 'gemini-pro')
            model = genai.GenerativeModel(model_name)

            response = await asyncio.wait_for(
                model.generate_content_async(prompt),
                timeout=timeout
            )

            return {
                'success': True,
                'output': response.text,
                'model': model_name,
            }

        except ImportError:
            logger.warning("google-generativeai package not installed")
            return await self._simulate_response(prompt)
        except Exception as e:
            logger.error("Google API error", error=str(e))
            return {'success': False, 'error': str(e)}

    async def _call_ollama(
        self,
        prompt: str,
        config: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """Call local Ollama API."""
        try:
            import httpx

            base_url = config.get('ollama_url', 'http://localhost:11434')
            model = config.get('model', 'llama2')

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/api/generate",
                    json={
                        'model': model,
                        'prompt': prompt,
                        'stream': False,
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()

                return {
                    'success': True,
                    'output': data.get('response', ''),
                    'model': model,
                }

        except Exception as e:
            logger.error("Ollama API error", error=str(e))
            return {'success': False, 'error': str(e)}

    async def _simulate_response(self, prompt: str) -> Dict[str, Any]:
        """Simulate API response for testing."""
        await asyncio.sleep(0.5)
        return {
            'success': True,
            'output': f"[Simulated] Response for prompt: {prompt[:100]}...",
            'model': 'simulated',
            'simulated': True,
        }

    def report_result(self, execution_id: str, result: Dict[str, Any]):
        """Called by worker to report task result."""
        self._results[execution_id] = result
        event = self._pending_results.get(execution_id)
        if event:
            event.set()


# Factory function
def get_task_executor(db: AsyncSession) -> TaskExecutor:
    """Create a task executor instance."""
    return TaskExecutor(db)
