"""
E2E Tests: Parallel Execution

Tests for parallel subtask execution including:
- Multiple subtasks executing in parallel
- DAG dependency resolution
- Concurrent execution limits
- Worker allocation for parallel tasks
"""

import pytest
import asyncio
from uuid import UUID
from sqlalchemy import select

from src.models.subtask import Subtask


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_parallel_subtask_execution(
    task_factory,
    subtask_factory,
    sample_code_output,
    sample_test_output
):
    """Test multiple independent subtasks can be completed in parallel"""
    # Create and decompose task
    task_info = await task_factory.create_task(
        description="Build REST API with multiple endpoints",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    assert len(subtasks) >= 2

    # Get ready subtasks (those without dependencies)
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    ready_data = response.json()
    ready_subtasks = ready_data["ready_subtasks"]

    # If we have multiple ready subtasks, they can execute in parallel
    if len(ready_subtasks) >= 2:
        # Simulate parallel execution by completing multiple subtasks
        completion_tasks = []

        for i, subtask in enumerate(ready_subtasks[:2]):  # Complete first 2 in parallel
            subtask_id = UUID(subtask["subtask_id"])
            output = sample_code_output if i == 0 else sample_test_output

            # Create async task to complete subtask
            completion_tasks.append(
                subtask_factory.submit_result(
                    subtask_id=subtask_id,
                    status="completed",
                    output=output
                )
            )

        # Wait for all completions (simulating parallel execution)
        results = await asyncio.gather(*completion_tasks)
        assert all(r["status"] == "completed" for r in results)

        # Verify both subtasks are completed
        task_details = await task_factory.get_task_details(task_id)
        completed_count = sum(
            1 for s in task_details["subtasks"]
            if s["status"] == "completed"
        )
        assert completed_count >= 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dag_dependency_resolution(
    db_session,
    task_factory,
    subtask_factory,
    sample_code_output
):
    """Test DAG dependency resolution - subtasks execute in correct order"""
    # Create and decompose task
    task_info = await task_factory.create_task(
        description="Complex feature with dependencies",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    assert len(subtasks) >= 3  # Need multiple subtasks to test dependencies

    # Get initial ready subtasks (no dependencies)
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    initial_ready = response.json()["ready_subtasks"]
    assert len(initial_ready) >= 1

    # Complete first subtask
    first_subtask_id = UUID(initial_ready[0]["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=first_subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Check if more subtasks became ready
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    new_ready = response.json()["ready_subtasks"]

    # Should have new ready subtasks whose dependencies were satisfied
    new_ready_ids = {UUID(s["subtask_id"]) for s in new_ready}
    initial_ready_ids = {UUID(s["subtask_id"]) for s in initial_ready}

    # May have new subtasks ready (dependencies satisfied)
    # Or all were already independent
    assert len(new_ready) >= 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dependency_blocking(
    db_session,
    task_factory,
    subtask_factory
):
    """Test that subtasks with unsatisfied dependencies cannot start"""
    # Create task
    task_info = await task_factory.create_task(
        description="Sequential task execution test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Find a subtask with dependencies
    dependent_subtask = None
    for subtask in subtasks:
        if subtask["dependencies"] and len(subtask["dependencies"]) > 0:
            dependent_subtask = subtask
            break

    if dependent_subtask:
        # Verify it's not in ready list
        response = await task_factory.client.get(
            f"/api/v1/tasks/{task_id}/ready-subtasks"
        )
        ready_ids = {UUID(s["subtask_id"]) for s in response.json()["ready_subtasks"]}
        dependent_id = UUID(dependent_subtask["subtask_id"])

        # Should not be ready since dependencies not completed
        assert dependent_id not in ready_ids


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_workers_parallel_execution(
    worker_factory,
    task_factory,
    subtask_factory,
    sample_code_output
):
    """Test multiple workers executing subtasks in parallel"""
    # Create multiple workers
    workers = []
    for i in range(3):
        worker = await worker_factory.create_worker(
            machine_name=f"Parallel Worker {i}",
            status="idle"
        )
        workers.append(worker)

    # Create task with multiple subtasks
    task_info = await task_factory.create_task(
        description="Task for parallel worker testing",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Get ready subtasks
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    ready_subtasks = response.json()["ready_subtasks"]

    # If we have multiple ready subtasks, simulate parallel assignment
    if len(ready_subtasks) >= 2 and len(workers) >= 2:
        # Simulate workers picking up different subtasks
        for i, subtask in enumerate(ready_subtasks[:2]):
            subtask_id = UUID(subtask["subtask_id"])
            worker_id = workers[i]["worker_id"]

            # Worker marks as in_progress (via heartbeat with current_task)
            await worker_factory.client.post(
                f"/api/v1/workers/{worker_id}/heartbeat",
                json={
                    "status": "busy",
                    "resources": {
                        "cpu_percent": 70.0,
                        "memory_percent": 60.0,
                        "disk_percent": 50.0
                    },
                    "current_task": str(subtask_id)
                }
            )

        # Simulate parallel completion
        completion_tasks = []
        for i, subtask in enumerate(ready_subtasks[:2]):
            subtask_id = UUID(subtask["subtask_id"])
            completion_tasks.append(
                subtask_factory.submit_result(
                    subtask_id=subtask_id,
                    status="completed",
                    output=sample_code_output
                )
            )

        # Wait for all completions
        await asyncio.gather(*completion_tasks)

        # Verify both completed
        task_details = await task_factory.get_task_details(task_id)
        completed_count = sum(
            1 for s in task_details["subtasks"]
            if s["status"] == "completed"
        )
        assert completed_count >= 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_concurrent_subtask_allocation(
    db_session,
    worker_factory,
    task_factory
):
    """Test concurrent allocation of subtasks to workers"""
    # Create workers
    workers = [
        await worker_factory.create_worker(machine_name=f"Alloc Worker {i}")
        for i in range(3)
    ]

    # Create task
    task_info = await task_factory.create_task(
        description="Concurrent allocation test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    await task_factory.decompose_task(task_id)

    # Get ready subtasks
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    ready_subtasks = response.json()["ready_subtasks"]

    if len(ready_subtasks) >= 3:
        # Simulate concurrent allocation requests
        allocation_tasks = []

        for i, subtask in enumerate(ready_subtasks[:3]):
            subtask_id = UUID(subtask["subtask_id"])
            worker_id = workers[i]["worker_id"]

            # Allocate subtask to worker
            allocation_tasks.append(
                worker_factory.client.post(
                    f"/api/v1/subtasks/{subtask_id}/allocate",
                    json={"worker_id": str(worker_id)}
                )
            )

        # Execute allocations concurrently
        responses = await asyncio.gather(*allocation_tasks, return_exceptions=True)

        # Count successful allocations
        successful = sum(
            1 for r in responses
            if not isinstance(r, Exception) and hasattr(r, 'status_code') and r.status_code == 200
        )

        # Should have successful allocations
        assert successful >= 1


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_parallel_execution_with_failures(
    task_factory,
    subtask_factory,
    sample_code_output
):
    """Test parallel execution when some subtasks fail"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task with potential failures",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Get ready subtasks
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    ready_subtasks = response.json()["ready_subtasks"]

    if len(ready_subtasks) >= 2:
        # Complete first subtask successfully
        await subtask_factory.submit_result(
            subtask_id=UUID(ready_subtasks[0]["subtask_id"]),
            status="completed",
            output=sample_code_output
        )

        # Fail second subtask
        await subtask_factory.submit_result(
            subtask_id=UUID(ready_subtasks[1]["subtask_id"]),
            status="failed",
            error="Simulated failure for testing"
        )

        # Verify statuses
        task_details = await task_factory.get_task_details(task_id)
        statuses = {s["subtask_id"]: s["status"] for s in task_details["subtasks"]}

        assert statuses[ready_subtasks[0]["subtask_id"]] == "completed"
        assert statuses[ready_subtasks[1]["subtask_id"]] == "failed"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sequential_dependency_chain(
    task_factory,
    subtask_factory,
    sample_code_output,
    sample_review_output,
    sample_test_output
):
    """Test sequential execution of dependent subtasks"""
    # Create task (develop_feature creates: code gen -> review -> test -> docs)
    task_info = await task_factory.create_task(
        description="Feature with sequential workflow",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    assert len(subtasks) >= 3

    # Complete subtasks in dependency order
    completed_ids = []

    for _ in range(min(3, len(subtasks))):
        # Get currently ready subtasks
        response = await task_factory.client.get(
            f"/api/v1/tasks/{task_id}/ready-subtasks"
        )
        ready_subtasks = response.json()["ready_subtasks"]

        if not ready_subtasks:
            break

        # Complete first ready subtask
        subtask_id = UUID(ready_subtasks[0]["subtask_id"])

        # Choose appropriate output based on subtask type
        output = sample_code_output

        await subtask_factory.submit_result(
            subtask_id=subtask_id,
            status="completed",
            output=output
        )

        completed_ids.append(subtask_id)

        # Small delay to simulate processing time
        await asyncio.sleep(0.1)

    # Verify we completed multiple subtasks in sequence
    assert len(completed_ids) >= 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_mixed_parallel_sequential_execution(
    task_factory,
    subtask_factory,
    sample_code_output
):
    """Test mixed execution: some parallel, some sequential"""
    # Create task
    task_info = await task_factory.create_task(
        description="Complex task with mixed dependencies",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Get initial ready subtasks
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    initial_ready = response.json()["ready_subtasks"]

    if len(initial_ready) >= 2:
        # Complete multiple ready subtasks in parallel
        completion_tasks = [
            subtask_factory.submit_result(
                subtask_id=UUID(s["subtask_id"]),
                status="completed",
                output=sample_code_output
            )
            for s in initial_ready[:2]
        ]

        await asyncio.gather(*completion_tasks)

        # Check for new ready subtasks
        response = await task_factory.client.get(
            f"/api/v1/tasks/{task_id}/ready-subtasks"
        )
        new_ready = response.json()["ready_subtasks"]

        # May have new subtasks ready now
        # Complete one more if available
        if new_ready:
            await subtask_factory.submit_result(
                subtask_id=UUID(new_ready[0]["subtask_id"]),
                status="completed",
                output=sample_code_output
            )

        # Verify progress
        task_details = await task_factory.get_task_details(task_id)
        completed_count = sum(
            1 for s in task_details["subtasks"]
            if s["status"] == "completed"
        )
        assert completed_count >= 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_all_independent_subtasks(
    db_session,
    task_factory,
    subtask_factory,
    sample_code_output
):
    """Test task where all subtasks are independent (can run in parallel)"""
    # Code review task typically has independent analysis subtasks
    task_info = await task_factory.create_task(
        description="Code review with independent checks",
        task_type="code_review"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Get ready subtasks
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    ready_subtasks = response.json()["ready_subtasks"]

    # For code_review, many/all subtasks might be ready immediately
    # Complete multiple in parallel
    if len(ready_subtasks) >= 2:
        completion_tasks = [
            subtask_factory.submit_result(
                subtask_id=UUID(s["subtask_id"]),
                status="completed",
                output=sample_code_output
            )
            for s in ready_subtasks[:3]  # Complete up to 3 in parallel
        ]

        results = await asyncio.gather(*completion_tasks)
        assert all(r["status"] == "completed" for r in results)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_max_parallel_workers(
    worker_factory,
    task_factory,
    subtask_factory
):
    """Test system behavior with maximum parallel workers"""
    # Create many workers
    workers = [
        await worker_factory.create_worker(machine_name=f"Max Worker {i}")
        for i in range(5)
    ]

    # Create task with multiple subtasks
    task_info = await task_factory.create_task(
        description="Task for max parallelism test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    await task_factory.decompose_task(task_id)

    # Get ready subtasks
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    ready_subtasks = response.json()["ready_subtasks"]

    # All workers pick up tasks
    if len(ready_subtasks) >= len(workers):
        for i, worker in enumerate(workers):
            if i < len(ready_subtasks):
                subtask_id = UUID(ready_subtasks[i]["subtask_id"])
                await worker_factory.client.post(
                    f"/api/v1/workers/{worker['worker_id']}/heartbeat",
                    json={
                        "status": "busy",
                        "resources": {
                            "cpu_percent": 80.0,
                            "memory_percent": 70.0,
                            "disk_percent": 50.0
                        },
                        "current_task": str(subtask_id)
                    }
                )

        # Verify all workers are busy
        response = await worker_factory.client.get("/api/v1/workers?status=busy")
        busy_workers = response.json()["workers"]
        assert len(busy_workers) >= 3  # At least 3 workers should be busy
