"""
E2E Test Configuration and Fixtures

Provides comprehensive fixtures for end-to-end testing including:
- Full system setup (database, redis, client)
- Data factories for creating test entities
- Helper functions for common E2E test scenarios
"""

import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from typing import Dict, List, Optional
from datetime import datetime

from src.models.task import Task
from src.models.subtask import Subtask
from src.models.worker import Worker
from src.models.checkpoint import Checkpoint
from src.models.evaluation import Evaluation


# ==================== Data Factory Fixtures ====================


class WorkerFactory:
    """Factory for creating test workers"""

    def __init__(self, db_session, test_client):
        self.db = db_session
        self.client = test_client
        self._workers = []

    async def create_worker(
        self,
        machine_id: Optional[str] = None,
        machine_name: str = "Test Worker",
        tools: Optional[List[str]] = None,
        status: str = "online"
    ) -> Dict:
        """Create a worker via API and return worker data"""
        if machine_id is None:
            machine_id = f"test-machine-{uuid4()}"

        if tools is None:
            tools = ["claude_code", "gemini_cli"]

        worker_data = {
            "machine_id": machine_id,
            "machine_name": machine_name,
            "system_info": {
                "os": "Linux",
                "os_version": "Ubuntu 22.04",
                "cpu_count": 8,
                "memory_total": 16000000000,
                "python_version": "3.11.0"
            },
            "tools": tools
        }

        response = await self.client.post(
            "/api/v1/workers/register",
            json=worker_data
        )
        assert response.status_code == 200

        result = response.json()
        worker_id = UUID(result["worker_id"])

        # Send heartbeat to set status
        await self.client.post(
            f"/api/v1/workers/{worker_id}/heartbeat",
            json={
                "status": status,
                "resources": {
                    "cpu_percent": 25.5,
                    "memory_percent": 60.2,
                    "disk_percent": 45.0
                }
            }
        )

        worker_info = {
            "worker_id": worker_id,
            "machine_id": machine_id,
            "machine_name": machine_name,
            "tools": tools,
            "status": status
        }
        self._workers.append(worker_info)
        return worker_info

    async def cleanup(self):
        """Cleanup all created workers"""
        for worker in self._workers:
            try:
                await self.client.post(
                    f"/api/v1/workers/{worker['worker_id']}/unregister"
                )
            except Exception:
                pass


class TaskFactory:
    """Factory for creating test tasks"""

    def __init__(self, db_session, test_client):
        self.db = db_session
        self.client = test_client
        self._tasks = []

    async def create_task(
        self,
        description: str = "Test task for E2E testing",
        task_type: str = "develop_feature",
        checkpoint_frequency: str = "medium",
        privacy_level: str = "normal",
        tool_preferences: Optional[List[str]] = None,
        requirements: Optional[Dict] = None
    ) -> Dict:
        """Create a task via API and return task data"""
        task_data = {
            "description": description,
            "task_type": task_type,
            "checkpoint_frequency": checkpoint_frequency,
            "privacy_level": privacy_level
        }

        if tool_preferences:
            task_data["tool_preferences"] = tool_preferences

        if requirements:
            task_data["requirements"] = requirements

        response = await self.client.post(
            "/api/v1/tasks",
            json=task_data
        )
        assert response.status_code == 201

        result = response.json()
        task_id = UUID(result["task_id"])

        task_info = {
            "task_id": task_id,
            "description": description,
            "task_type": task_type,
            "status": result["status"]
        }
        self._tasks.append(task_info)
        return task_info

    async def decompose_task(self, task_id: UUID) -> List[Dict]:
        """Decompose a task into subtasks"""
        response = await self.client.post(
            f"/api/v1/tasks/{task_id}/decompose"
        )
        assert response.status_code == 200

        result = response.json()
        return result["subtasks"]

    async def get_task_details(self, task_id: UUID) -> Dict:
        """Get detailed task information"""
        response = await self.client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        return response.json()

    async def cleanup(self):
        """Cleanup all created tasks"""
        for task in self._tasks:
            try:
                await self.client.post(
                    f"/api/v1/tasks/{task['task_id']}/cancel"
                )
            except Exception:
                pass


class SubtaskFactory:
    """Factory for managing subtasks in E2E tests"""

    def __init__(self, db_session, test_client):
        self.db = db_session
        self.client = test_client

    async def submit_result(
        self,
        subtask_id: UUID,
        status: str = "completed",
        output: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> Dict:
        """Submit subtask result"""
        result_data = {
            "status": status
        }

        if output:
            result_data["output"] = output
        if error:
            result_data["error"] = error

        response = await self.client.post(
            f"/api/v1/subtasks/{subtask_id}/result",
            json=result_data
        )
        assert response.status_code == 200
        return response.json()

    async def get_subtask_details(self, subtask_id: UUID) -> Dict:
        """Get subtask details"""
        response = await self.client.get(f"/api/v1/subtasks/{subtask_id}")
        assert response.status_code == 200
        return response.json()


class EvaluationFactory:
    """Factory for creating test evaluations"""

    def __init__(self, db_session):
        self.db = db_session

    async def create_evaluation(
        self,
        subtask_id: UUID,
        code_quality: float = 8.0,
        completeness: float = 9.0,
        security: float = 8.5,
        architecture: float = 7.5,
        testability: float = 8.0
    ) -> Evaluation:
        """Create an evaluation record directly in database"""
        evaluation = Evaluation(
            subtask_id=subtask_id,
            code_quality=code_quality,
            completeness=completeness,
            security=security,
            architecture=architecture,
            testability=testability
        )
        evaluation.overall_score = evaluation.calculate_overall_score()

        self.db.add(evaluation)
        await self.db.commit()
        await self.db.refresh(evaluation)

        return evaluation


# ==================== E2E Test Fixtures ====================


@pytest_asyncio.fixture
async def worker_factory(db_session, test_client):
    """Provide a WorkerFactory instance"""
    factory = WorkerFactory(db_session, test_client)
    yield factory
    await factory.cleanup()


@pytest_asyncio.fixture
async def task_factory(db_session, test_client):
    """Provide a TaskFactory instance"""
    factory = TaskFactory(db_session, test_client)
    yield factory
    await factory.cleanup()


@pytest_asyncio.fixture
async def subtask_factory(db_session, test_client):
    """Provide a SubtaskFactory instance"""
    return SubtaskFactory(db_session, test_client)


@pytest_asyncio.fixture
async def evaluation_factory(db_session):
    """Provide an EvaluationFactory instance"""
    return EvaluationFactory(db_session)


@pytest_asyncio.fixture
async def e2e_system(worker_factory, task_factory, subtask_factory, evaluation_factory):
    """
    Provide a complete E2E system setup with factories

    This fixture bundles all factories for convenient access in E2E tests.
    """
    return {
        "workers": worker_factory,
        "tasks": task_factory,
        "subtasks": subtask_factory,
        "evaluations": evaluation_factory
    }


# ==================== Helper Fixtures ====================


@pytest.fixture
def sample_code_output():
    """Sample code generation output for testing"""
    return {
        "text": "Successfully generated authentication module",
        "files": [
            {
                "path": "src/auth/authentication.py",
                "content": "# Authentication implementation\n\nclass AuthService:\n    pass",
                "action": "created"
            },
            {
                "path": "tests/test_auth.py",
                "content": "# Auth tests\n\ndef test_auth():\n    pass",
                "action": "created"
            }
        ],
        "usage": {
            "input_tokens": 1500,
            "output_tokens": 800,
            "total_tokens": 2300
        }
    }


@pytest.fixture
def sample_review_output():
    """Sample code review output for testing"""
    return {
        "text": "Code review completed. Found 2 minor issues.",
        "files": [],
        "issues": [
            {
                "severity": "minor",
                "file": "src/auth/authentication.py",
                "line": 15,
                "message": "Consider adding input validation"
            },
            {
                "severity": "minor",
                "file": "src/auth/authentication.py",
                "line": 23,
                "message": "Missing docstring for public method"
            }
        ],
        "usage": {
            "input_tokens": 2000,
            "output_tokens": 500,
            "total_tokens": 2500
        }
    }


@pytest.fixture
def sample_test_output():
    """Sample test generation output for testing"""
    return {
        "text": "Generated comprehensive test suite",
        "files": [
            {
                "path": "tests/test_authentication.py",
                "content": "import pytest\n\nclass TestAuth:\n    pass",
                "action": "created"
            }
        ],
        "test_results": {
            "total": 10,
            "passed": 10,
            "failed": 0,
            "skipped": 0
        },
        "usage": {
            "input_tokens": 1200,
            "output_tokens": 600,
            "total_tokens": 1800
        }
    }


# ==================== Async Helper Functions ====================


async def wait_for_task_status(
    test_client,
    task_id: UUID,
    expected_status: str,
    timeout: int = 30,
    interval: float = 0.5
) -> bool:
    """
    Wait for task to reach expected status

    Args:
        test_client: Test client instance
        task_id: Task UUID
        expected_status: Expected status string
        timeout: Maximum wait time in seconds
        interval: Poll interval in seconds

    Returns:
        True if status reached, False if timeout
    """
    import asyncio

    start_time = asyncio.get_event_loop().time()

    while True:
        response = await test_client.get(f"/api/v1/tasks/{task_id}")
        if response.status_code == 200:
            data = response.json()
            if data["status"] == expected_status:
                return True

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            return False

        await asyncio.sleep(interval)


async def wait_for_subtask_status(
    test_client,
    subtask_id: UUID,
    expected_status: str,
    timeout: int = 30,
    interval: float = 0.5
) -> bool:
    """
    Wait for subtask to reach expected status

    Args:
        test_client: Test client instance
        subtask_id: Subtask UUID
        expected_status: Expected status string
        timeout: Maximum wait time in seconds
        interval: Poll interval in seconds

    Returns:
        True if status reached, False if timeout
    """
    import asyncio

    start_time = asyncio.get_event_loop().time()

    while True:
        response = await test_client.get(f"/api/v1/subtasks/{subtask_id}")
        if response.status_code == 200:
            data = response.json()
            if data["status"] == expected_status:
                return True

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            return False

        await asyncio.sleep(interval)
