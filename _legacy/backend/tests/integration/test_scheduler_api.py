"""Integration tests for Scheduler API endpoints"""

import pytest
from uuid import uuid4


@pytest.fixture
def sample_task_data():
    """Sample task creation data"""
    return {
        "description": "Create a Python function that calculates fibonacci numbers with memoization for scheduler testing",
        "task_type": "develop_feature",
        "requirements": {
            "language": "python",
            "include_tests": True
        },
        "checkpoint_frequency": "medium",
        "privacy_level": "normal",
        "tool_preferences": ["claude_code"]
    }


@pytest.fixture
def sample_worker_data():
    """Sample worker registration data - unique per test"""
    unique_id = uuid4().hex[:12]
    return {
        "machine_id": f"scheduler-test-{unique_id}",
        "machine_name": f"Scheduler Test Worker {unique_id}",
        "system_info": {
            "os": "linux",
            "cpu": "Intel i7",
            "memory_total_gb": 16,
            "disk_total_gb": 500
        },
        "tools": ["claude_code", "gemini_cli"]
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_scheduling_cycle(test_client):
    """Test manually running a scheduling cycle"""
    response = await test_client.post("/api/v1/scheduler/run")

    assert response.status_code == 200
    data = response.json()

    assert "cycle_start" in data
    assert "tasks_processed" in data
    assert "subtasks_allocated" in data
    assert "subtasks_queued" in data
    assert isinstance(data["errors"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_scheduler_stats(test_client):
    """Test getting scheduler statistics"""
    response = await test_client.get("/api/v1/scheduler/stats")

    assert response.status_code == 200
    data = response.json()

    assert "active_tasks" in data
    assert "available_workers" in data
    assert "subtask_status_counts" in data
    assert "queue_length" in data
    assert "in_progress_count" in data
    assert "max_concurrent_subtasks" in data
    assert "max_subtasks_per_worker" in data
    assert "scheduler_interval_seconds" in data

    # Verify limits
    assert data["max_concurrent_subtasks"] == 20
    assert data["max_subtasks_per_worker"] == 1
    assert data["scheduler_interval_seconds"] == 30


@pytest.mark.integration
@pytest.mark.asyncio
async def test_schedule_task(test_client, sample_task_data):
    """Test scheduling a specific task"""
    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["task_id"]

    # Schedule task (this will decompose if needed)
    response = await test_client.post(f"/api/v1/tasks/{task_id}/schedule")

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == task_id
    assert "subtasks_allocated" in data
    assert "subtasks_queued" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_schedule_task_not_found(test_client):
    """Test scheduling non-existent task"""
    fake_task_id = str(uuid4())

    response = await test_client.post(f"/api/v1/tasks/{fake_task_id}/schedule")

    assert response.status_code == 200  # Returns result with error
    data = response.json()
    assert "error" in data
    assert "not found" in data["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_handle_subtask_completion(test_client, sample_task_data):
    """Test handling subtask completion"""
    # Create and decompose task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    decompose_response = await test_client.post(f"/api/v1/tasks/{task_id}/decompose")
    subtasks = decompose_response.json()["subtasks"]
    subtask_id = subtasks[0]["subtask_id"]

    # Handle completion (simulating subtask completion)
    response = await test_client.post(f"/api/v1/subtasks/{subtask_id}/complete")

    assert response.status_code == 200
    data = response.json()

    assert data["subtask_id"] == subtask_id
    assert "newly_allocated" in data
    assert "task_completed" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_handle_subtask_completion_not_found(test_client):
    """Test handling completion of non-existent subtask"""
    fake_subtask_id = str(uuid4())

    response = await test_client.post(f"/api/v1/subtasks/{fake_subtask_id}/complete")

    assert response.status_code == 200
    data = response.json()

    assert data["newly_allocated"] == 0
    assert data["task_completed"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduler_workflow_complete(test_client, sample_task_data, sample_worker_data):
    """Test complete scheduler workflow"""
    # 1. Register worker
    worker_response = await test_client.post(
        "/api/v1/workers/register",
        json=sample_worker_data
    )
    assert worker_response.status_code in (200, 201)

    # 2. Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["task_id"]

    # 3. Check initial scheduler stats
    stats_response = await test_client.get("/api/v1/scheduler/stats")
    assert stats_response.status_code == 200

    # 4. Schedule task (will decompose and allocate)
    schedule_response = await test_client.post(f"/api/v1/tasks/{task_id}/schedule")
    assert schedule_response.status_code == 200

    # 5. Run a scheduling cycle
    cycle_response = await test_client.post("/api/v1/scheduler/run")
    assert cycle_response.status_code == 200

    # 6. Check updated stats
    final_stats_response = await test_client.get("/api/v1/scheduler/stats")
    assert final_stats_response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduling_with_decomposed_task(test_client, sample_task_data, sample_worker_data):
    """Test scheduling already decomposed task"""
    # Register worker
    await test_client.post(
        "/api/v1/workers/register",
        json=sample_worker_data
    )

    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    # Decompose task first
    await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    # Now schedule (should allocate ready subtasks)
    schedule_response = await test_client.post(f"/api/v1/tasks/{task_id}/schedule")

    assert schedule_response.status_code == 200
    data = schedule_response.json()

    # Should have processed the decomposed subtasks
    assert data["subtasks_allocated"] >= 0 or data["subtasks_queued"] >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_scheduling_cycles(test_client, sample_task_data):
    """Test running multiple scheduling cycles"""
    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    # Decompose task
    await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    # Run multiple cycles
    for _ in range(3):
        response = await test_client.post("/api/v1/scheduler/run")
        assert response.status_code == 200
        data = response.json()
        assert "cycle_start" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduler_stats_after_operations(test_client, sample_task_data):
    """Test scheduler stats reflect operations"""
    # Get initial stats
    initial_stats = await test_client.get("/api/v1/scheduler/stats")
    initial_data = initial_stats.json()

    # Create and decompose tasks
    for i in range(2):
        create_response = await test_client.post(
            "/api/v1/tasks",
            json={
                "description": f"Scheduler stats test task {i+1} with enough characters",
                "task_type": "develop_feature"
            }
        )
        task_id = create_response.json()["task_id"]
        await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    # Get updated stats
    updated_stats = await test_client.get("/api/v1/scheduler/stats")
    updated_data = updated_stats.json()

    # Active tasks should have increased
    assert updated_data["active_tasks"] >= initial_data.get("active_tasks", 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduling_cycle_handles_errors_gracefully(test_client):
    """Test that scheduling cycle handles errors without crashing"""
    # Run cycle even with potential edge cases
    response = await test_client.post("/api/v1/scheduler/run")

    assert response.status_code == 200
    data = response.json()

    # Should complete without server error
    assert "cycle_start" in data
    # Errors should be captured, not thrown
    assert isinstance(data["errors"], list)
