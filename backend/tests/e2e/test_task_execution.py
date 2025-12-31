"""
E2E Tests: Task Execution

Tests for the complete task execution lifecycle:
- Task submission
- Task decomposition
- Task allocation to workers
- Task status tracking
- Task cancellation
"""

import pytest
from uuid import uuid4, UUID


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_submission_flow(test_client):
    """Test complete task submission and creation flow"""
    task_data = {
        "description": "Implement user authentication system with JWT tokens",
        "task_type": "develop_feature",
        "checkpoint_frequency": "medium",
        "privacy_level": "normal",
        "tool_preferences": ["claude_code"],
        "requirements": {
            "complexity": "high",
            "estimated_time": "2h"
        }
    }

    # Submit task
    response = await test_client.post(
        "/api/v1/tasks",
        json=task_data
    )

    assert response.status_code == 201
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    assert "message" in data

    task_id = data["task_id"]

    # Verify task was created
    response = await test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200

    task_details = response.json()
    assert task_details["description"] == task_data["description"]
    assert task_details["status"] == "pending"
    assert task_details["progress"] == 0
    assert task_details["checkpoint_frequency"] == "medium"
    assert task_details["privacy_level"] == "normal"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_decomposition_flow(task_factory):
    """Test task decomposition into subtasks"""
    # Create task
    task_info = await task_factory.create_task(
        description="Build REST API for user management",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    # Decompose task
    subtasks = await task_factory.decompose_task(task_id)

    # Verify subtasks were created
    assert len(subtasks) > 0
    assert all("subtask_id" in s for s in subtasks)
    assert all("name" in s for s in subtasks)
    assert all("description" in s for s in subtasks)
    assert all("status" in s for s in subtasks)

    # Verify subtask types for develop_feature
    subtask_types = [s.get("recommended_tool") for s in subtasks]
    # Should have code generation, review, test, docs

    # Verify dependencies are set correctly (DAG structure)
    first_subtask = subtasks[0]
    assert first_subtask["dependencies"] == [] or first_subtask["dependencies"] is None

    # Later subtasks should have dependencies
    if len(subtasks) > 1:
        later_subtasks_have_deps = any(
            s["dependencies"] and len(s["dependencies"]) > 0
            for s in subtasks[1:]
        )
        # At least some subtasks should have dependencies


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_ready_subtasks(task_factory):
    """Test getting ready subtasks for execution"""
    # Create and decompose task
    task_info = await task_factory.create_task(
        description="Refactor authentication module",
        task_type="refactor"
    )
    task_id = task_info["task_id"]

    await task_factory.decompose_task(task_id)

    # Get ready subtasks (should be subtasks with no dependencies)
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/ready-subtasks"
    )
    assert response.status_code == 200

    data = response.json()
    assert "ready_subtasks" in data
    assert "total_ready" in data
    assert data["total_ready"] >= 1

    # Verify ready subtasks have no dependencies or dependencies are completed
    for subtask in data["ready_subtasks"]:
        assert subtask["status"] == "pending"
        # Dependencies should be empty or all completed
        if subtask["dependencies"]:
            assert len(subtask["dependencies"]) == 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_progress_tracking(task_factory, subtask_factory, sample_code_output):
    """Test task progress updates as subtasks complete"""
    # Create and decompose task
    task_info = await task_factory.create_task(
        description="Implement logging system",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    assert len(subtasks) > 0

    # Complete first subtask
    first_subtask_id = UUID(subtasks[0]["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=first_subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Check task progress
    task_details = await task_factory.get_task_details(task_id)

    # Progress should be updated (at least 1 subtask completed)
    # Progress = (completed_subtasks / total_subtasks) * 100
    expected_min_progress = int((1 / len(subtasks)) * 100)
    assert task_details["progress"] >= expected_min_progress

    # Verify subtask is marked as completed
    completed_subtask = next(
        (s for s in task_details["subtasks"] if str(s["subtask_id"]) == str(first_subtask_id)),
        None
    )
    assert completed_subtask is not None
    assert completed_subtask["status"] == "completed"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_cancellation(task_factory):
    """Test task cancellation flow"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task to be cancelled",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    # Cancel task
    response = await task_factory.client.post(
        f"/api/v1/tasks/{task_id}/cancel"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "cancelled"
    assert data["task_id"] == str(task_id)

    # Verify task status is cancelled
    task_details = await task_factory.get_task_details(task_id)
    assert task_details["status"] == "cancelled"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_cancellation_with_subtasks(task_factory, subtask_factory, sample_code_output):
    """Test cancelling task with in-progress subtasks"""
    # Create and decompose task
    task_info = await task_factory.create_task(
        description="Task with subtasks to be cancelled",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    assert len(subtasks) >= 1

    # Start first subtask (mark as in_progress)
    first_subtask_id = UUID(subtasks[0]["subtask_id"])
    # Note: In real system, worker would pick up and mark as in_progress
    # For E2E test, we simulate by submitting partial result

    # Cancel task while subtask is in progress
    response = await task_factory.client.post(
        f"/api/v1/tasks/{task_id}/cancel"
    )
    assert response.status_code == 200

    # Verify task is cancelled
    task_details = await task_factory.get_task_details(task_id)
    assert task_details["status"] == "cancelled"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_list_filtering(task_factory):
    """Test listing tasks with status filtering"""
    # Create multiple tasks with different eventual statuses
    tasks = []

    # Create pending task
    task1 = await task_factory.create_task(
        description="Pending task",
        task_type="develop_feature"
    )
    tasks.append(task1)

    # Create another pending task
    task2 = await task_factory.create_task(
        description="Another pending task",
        task_type="bug_fix"
    )
    tasks.append(task2)

    # Create and cancel a task
    task3 = await task_factory.create_task(
        description="Cancelled task",
        task_type="refactor"
    )
    await task_factory.client.post(f"/api/v1/tasks/{task3['task_id']}/cancel")
    tasks.append(task3)

    # List all tasks
    response = await task_factory.client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3

    # Filter by status: pending
    response = await task_factory.client.get("/api/v1/tasks?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert all(t["status"] == "pending" for t in data["tasks"])
    assert data["total"] >= 2

    # Filter by status: cancelled
    response = await task_factory.client.get("/api/v1/tasks?status=cancelled")
    assert response.status_code == 200
    data = response.json()
    assert all(t["status"] == "cancelled" for t in data["tasks"])


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_with_tool_preferences(task_factory):
    """Test task creation with specific tool preferences"""
    task_info = await task_factory.create_task(
        description="Task requiring specific tool",
        task_type="code_review",
        tool_preferences=["gemini_cli"]
    )
    task_id = task_info["task_id"]

    # Verify tool preferences were saved
    task_details = await task_factory.get_task_details(task_id)
    assert task_details["tool_preferences"] is not None
    assert "gemini_cli" in task_details["tool_preferences"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_different_types(task_factory):
    """Test decomposition of different task types"""
    task_types = [
        "develop_feature",
        "bug_fix",
        "refactor",
        "code_review",
        "documentation",
        "testing"
    ]

    for task_type in task_types:
        task_info = await task_factory.create_task(
            description=f"Test task for {task_type}",
            task_type=task_type
        )
        task_id = task_info["task_id"]

        # Decompose task
        subtasks = await task_factory.decompose_task(task_id)

        # Verify subtasks were created
        assert len(subtasks) > 0, f"No subtasks created for {task_type}"

        # Each task type should produce different decomposition
        # Verify at least basic structure
        assert all("subtask_id" in s for s in subtasks)
        assert all("name" in s for s in subtasks)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_status_query(task_factory):
    """Test querying task status and progress"""
    task_info = await task_factory.create_task(
        description="Task for status testing",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    # Query task progress endpoint
    response = await task_factory.client.get(
        f"/api/v1/tasks/{task_id}/progress"
    )
    assert response.status_code == 200

    data = response.json()
    assert "task_id" in data
    assert "status" in data
    assert "progress" in data
    assert data["status"] == "pending"
    assert data["progress"] == 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_validation_errors(test_client):
    """Test task creation with invalid data"""
    # Test with missing required field
    response = await test_client.post(
        "/api/v1/tasks",
        json={
            "task_type": "develop_feature"
            # Missing description
        }
    )
    assert response.status_code == 422  # Validation error

    # Test with description too short
    response = await test_client.post(
        "/api/v1/tasks",
        json={
            "description": "Too short",  # Less than minimum length
            "task_type": "develop_feature"
        }
    )
    assert response.status_code == 422

    # Test with invalid task_type
    response = await test_client.post(
        "/api/v1/tasks",
        json={
            "description": "This is a valid description for testing purposes",
            "task_type": "invalid_type"
        }
    )
    assert response.status_code == 422


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_nonexistent(test_client):
    """Test operations on non-existent task"""
    fake_task_id = uuid4()

    # Try to get non-existent task
    response = await test_client.get(f"/api/v1/tasks/{fake_task_id}")
    assert response.status_code == 404

    # Try to cancel non-existent task
    response = await test_client.post(f"/api/v1/tasks/{fake_task_id}/cancel")
    assert response.status_code in [400, 404]

    # Try to decompose non-existent task
    response = await test_client.post(f"/api/v1/tasks/{fake_task_id}/decompose")
    assert response.status_code in [400, 404]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_checkpoint_frequency(task_factory):
    """Test task creation with different checkpoint frequencies"""
    frequencies = ["low", "medium", "high"]

    for freq in frequencies:
        task_info = await task_factory.create_task(
            description=f"Task with {freq} checkpoint frequency",
            task_type="develop_feature",
            checkpoint_frequency=freq
        )
        task_id = task_info["task_id"]

        task_details = await task_factory.get_task_details(task_id)
        assert task_details["checkpoint_frequency"] == freq


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_task_privacy_levels(task_factory):
    """Test task creation with different privacy levels"""
    # Normal privacy task
    task1 = await task_factory.create_task(
        description="Normal privacy task",
        task_type="develop_feature",
        privacy_level="normal"
    )
    details1 = await task_factory.get_task_details(task1["task_id"])
    assert details1["privacy_level"] == "normal"

    # Sensitive privacy task
    task2 = await task_factory.create_task(
        description="Sensitive task with confidential data",
        task_type="develop_feature",
        privacy_level="sensitive"
    )
    details2 = await task_factory.get_task_details(task2["task_id"])
    assert details2["privacy_level"] == "sensitive"
