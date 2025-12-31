"""Integration tests for Tasks API endpoints"""

import pytest
from uuid import uuid4


@pytest.fixture
def sample_task_data():
    """Sample task creation data"""
    return {
        "description": "Create a Python function that calculates fibonacci numbers with memoization for testing",
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
def minimal_task_data():
    """Minimal task creation data"""
    return {
        "description": "This is a minimal task description for testing purposes"
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_success(test_client, sample_task_data):
    """Test successful task creation"""
    response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )

    assert response.status_code == 201
    data = response.json()

    assert "task_id" in data
    assert "status" in data
    assert data["status"] == "pending"
    assert "message" in data
    assert data["message"] == "Task created successfully"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_minimal(test_client, minimal_task_data):
    """Test task creation with minimal data"""
    response = await test_client.post(
        "/api/v1/tasks",
        json=minimal_task_data
    )

    assert response.status_code == 201
    data = response.json()

    assert "task_id" in data
    assert data["status"] == "pending"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_validation_error_short_description(test_client):
    """Test task creation with too short description"""
    response = await test_client.post(
        "/api/v1/tasks",
        json={
            "description": "Short"  # Less than 10 chars
        }
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_validation_error_missing_description(test_client):
    """Test task creation without description"""
    response = await test_client.post(
        "/api/v1/tasks",
        json={
            "task_type": "develop_feature"
        }
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks(test_client, sample_task_data):
    """Test listing tasks"""
    # Create a task first
    await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )

    # List tasks
    response = await test_client.get("/api/v1/tasks")

    assert response.status_code == 200
    data = response.json()

    assert "tasks" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["tasks"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks_with_filters(test_client):
    """Test listing tasks with status filter"""
    response = await test_client.get(
        "/api/v1/tasks",
        params={"status": "pending", "limit": 10, "offset": 0}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["limit"] == 10
    assert data["offset"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks_pagination(test_client, minimal_task_data):
    """Test task listing pagination"""
    # Create multiple tasks
    for i in range(3):
        await test_client.post(
            "/api/v1/tasks",
            json={
                "description": f"Test task for pagination testing number {i+1}"
            }
        )

    # Get first page
    response = await test_client.get(
        "/api/v1/tasks",
        params={"limit": 2, "offset": 0}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) <= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_detail(test_client, sample_task_data):
    """Test getting task details"""
    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["task_id"]

    # Get task details
    response = await test_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == task_id
    assert data["description"] == sample_task_data["description"]
    assert data["status"] == "pending"
    assert data["progress"] == 0
    assert "checkpoint_frequency" in data
    assert "privacy_level" in data
    assert "subtasks" in data
    assert isinstance(data["subtasks"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_not_found(test_client):
    """Test getting non-existent task"""
    fake_task_id = str(uuid4())

    response = await test_client.get(f"/api/v1/tasks/{fake_task_id}")

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_task(test_client, sample_task_data):
    """Test cancelling a task"""
    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["task_id"]

    # Cancel task
    response = await test_client.post(f"/api/v1/tasks/{task_id}/cancel")

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == task_id
    assert data["status"] == "cancelled"
    assert data["message"] == "Task cancelled successfully"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_task_not_found(test_client):
    """Test cancelling non-existent task"""
    fake_task_id = str(uuid4())

    response = await test_client.post(f"/api/v1/tasks/{fake_task_id}/cancel")

    assert response.status_code == 400  # ValueError -> Bad Request


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_already_cancelled_task(test_client, sample_task_data):
    """Test that already cancelled task returns error"""
    # Create and cancel task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    # First cancel
    await test_client.post(f"/api/v1/tasks/{task_id}/cancel")

    # Second cancel should fail
    response = await test_client.post(f"/api/v1/tasks/{task_id}/cancel")

    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_progress(test_client, sample_task_data):
    """Test getting task progress"""
    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    # Get progress
    response = await test_client.get(f"/api/v1/tasks/{task_id}/progress")

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == task_id
    assert "status" in data
    assert "progress" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_lifecycle(test_client):
    """Test complete task lifecycle: create -> get details -> cancel"""
    # 1. Create task
    task_data = {
        "description": "Complete lifecycle test task with all operations tested",
        "task_type": "develop_feature",
        "checkpoint_frequency": "high"
    }

    create_response = await test_client.post(
        "/api/v1/tasks",
        json=task_data
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["task_id"]

    # 2. Get task details
    detail_response = await test_client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "pending"

    # 3. Get progress
    progress_response = await test_client.get(f"/api/v1/tasks/{task_id}/progress")
    assert progress_response.status_code == 200

    # 4. Cancel task
    cancel_response = await test_client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    # 5. Verify cancelled status
    final_response = await test_client.get(f"/api/v1/tasks/{task_id}")
    assert final_response.status_code == 200
    assert final_response.json()["status"] == "cancelled"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_with_all_options(test_client):
    """Test creating task with all optional parameters"""
    task_data = {
        "description": "Full featured task with all options specified for comprehensive testing",
        "task_type": "bug_fix",
        "requirements": {
            "language": "python",
            "framework": "fastapi",
            "include_tests": True,
            "coverage_target": 80
        },
        "checkpoint_frequency": "high",
        "privacy_level": "sensitive",
        "tool_preferences": ["claude_code", "gemini_cli", "ollama"]
    }

    response = await test_client.post(
        "/api/v1/tasks",
        json=task_data
    )

    assert response.status_code == 201
    task_id = response.json()["task_id"]

    # Verify details
    detail_response = await test_client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.status_code == 200
    data = detail_response.json()

    assert data["checkpoint_frequency"] == "high"
    assert data["privacy_level"] == "sensitive"
    assert data["tool_preferences"] == ["claude_code", "gemini_cli", "ollama"]


# ==================== Task Decomposition Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decompose_task_success(test_client, sample_task_data):
    """Test successful task decomposition"""
    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["task_id"]

    # Decompose task
    response = await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == task_id
    assert data["subtask_count"] == 4  # develop_feature has 4 subtasks
    assert len(data["subtasks"]) == 4
    assert "message" in data

    # Verify subtasks
    subtask_names = [s["name"] for s in data["subtasks"]]
    assert "Code Generation" in subtask_names
    assert "Code Review" in subtask_names
    assert "Test Generation" in subtask_names
    assert "Documentation" in subtask_names


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decompose_task_not_found(test_client):
    """Test decomposing non-existent task"""
    fake_task_id = str(uuid4())

    response = await test_client.post(f"/api/v1/tasks/{fake_task_id}/decompose")

    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decompose_task_already_decomposed(test_client, sample_task_data):
    """Test that decomposing twice fails"""
    # Create and decompose task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    # First decomposition
    await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    # Second decomposition should fail
    response = await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    assert response.status_code == 400
    assert "already has subtasks" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decompose_task_updates_status(test_client, sample_task_data):
    """Test that decomposition updates task status to initializing"""
    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    # Decompose
    await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    # Check task status
    detail_response = await test_client.get(f"/api/v1/tasks/{task_id}")
    data = detail_response.json()

    assert data["status"] == "initializing"
    assert len(data["subtasks"]) == 4


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_ready_subtasks(test_client, sample_task_data):
    """Test getting ready subtasks after decomposition"""
    # Create and decompose task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    # Get ready subtasks
    response = await test_client.get(f"/api/v1/tasks/{task_id}/ready-subtasks")

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == task_id
    assert "ready_subtasks" in data
    assert "total_ready" in data

    # Code Generation should be ready (no dependencies)
    ready_names = [s["name"] for s in data["ready_subtasks"]]
    assert "Code Generation" in ready_names


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decompose_bug_fix_task(test_client):
    """Test decomposing a bug_fix task"""
    task_data = {
        "description": "Fix the authentication bug that causes login failures",
        "task_type": "bug_fix"
    }

    create_response = await test_client.post(
        "/api/v1/tasks",
        json=task_data
    )
    task_id = create_response.json()["task_id"]

    response = await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    assert response.status_code == 200
    data = response.json()

    assert data["subtask_count"] == 3  # bug_fix has 3 subtasks
    subtask_names = [s["name"] for s in data["subtasks"]]
    assert "Bug Analysis" in subtask_names
    assert "Fix Implementation" in subtask_names
    assert "Regression Testing" in subtask_names


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subtask_dependencies_structure(test_client, sample_task_data):
    """Test that subtask dependencies are properly set"""
    # Create and decompose task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    response = await test_client.post(f"/api/v1/tasks/{task_id}/decompose")
    subtasks = response.json()["subtasks"]

    # Code Generation should have no dependencies
    code_gen = next(s for s in subtasks if s["name"] == "Code Generation")
    assert code_gen["dependencies"] == []

    # Documentation should depend on Code Review and Test Generation
    documentation = next(s for s in subtasks if s["name"] == "Documentation")
    assert len(documentation["dependencies"]) == 2


# ==================== Real-time Status Query Tests (Story 3.5) ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_detail_includes_subtasks(test_client, sample_task_data):
    """Test that task detail includes subtasks after decomposition"""
    # Create and decompose task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    # Get task details
    response = await test_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()

    assert "subtasks" in data
    assert len(data["subtasks"]) == 4  # develop_feature has 4 subtasks

    # Verify subtask structure
    for subtask in data["subtasks"]:
        assert "subtask_id" in subtask
        assert "name" in subtask
        assert "status" in subtask
        assert "progress" in subtask
        assert "assigned_worker" in subtask
        assert "assigned_tool" in subtask
        # evaluation may be None for subtasks without evaluations
        assert "evaluation" in subtask


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_detail_evaluation_field(test_client, sample_task_data):
    """Test that task detail includes evaluation field for subtasks"""
    # Create and decompose task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    await test_client.post(f"/api/v1/tasks/{task_id}/decompose")

    # Get task details
    response = await test_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()

    # All subtasks should have evaluation field (may be None)
    for subtask in data["subtasks"]:
        assert "evaluation" in subtask
        # For newly created subtasks, evaluation should be None
        assert subtask["evaluation"] is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_realtime_status_workflow(test_client, sample_task_data):
    """Test complete workflow with real-time status query"""
    # 1. Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["task_id"]

    # 2. Verify initial status
    detail_response = await test_client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "pending"
    assert detail_response.json()["progress"] == 0

    # 3. Decompose task
    decompose_response = await test_client.post(f"/api/v1/tasks/{task_id}/decompose")
    assert decompose_response.status_code == 200

    # 4. Verify status changed to initializing
    detail_response = await test_client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "initializing"

    # 5. Verify subtasks are included with correct structure
    data = detail_response.json()
    assert len(data["subtasks"]) == 4
    for subtask in data["subtasks"]:
        assert subtask["status"] == "pending"
        assert subtask["progress"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_status_from_redis_and_db(test_client, sample_task_data):
    """Test that status is retrieved correctly when combining Redis and DB"""
    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    # Get task details - should work even if Redis cache is empty
    response = await test_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()

    # Should have valid data from DB fallback
    assert data["task_id"] == task_id
    assert data["status"] in ["pending", "initializing", "in_progress", "completed", "failed", "cancelled", "checkpoint"]
    assert 0 <= data["progress"] <= 100


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_not_found_returns_404(test_client):
    """Test that non-existent task returns 404"""
    fake_task_id = str(uuid4())

    response = await test_client.get(f"/api/v1/tasks/{fake_task_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_detail_response_structure(test_client, sample_task_data):
    """Test that task detail response has all required fields"""
    # Create task
    create_response = await test_client.post(
        "/api/v1/tasks",
        json=sample_task_data
    )
    task_id = create_response.json()["task_id"]

    # Get task details
    response = await test_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields
    assert "task_id" in data
    assert "description" in data
    assert "status" in data
    assert "progress" in data
    assert "checkpoint_frequency" in data
    assert "privacy_level" in data
    assert "tool_preferences" in data
    assert "task_metadata" in data
    assert "subtasks" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "started_at" in data
    assert "completed_at" in data
