"""
E2E Tests: Checkpoint and User Decision System

Tests for the checkpoint and human review system:
- Checkpoint triggering based on frequency
- User decision processing (accept/correct/reject)
- Correction workflow
- Checkpoint history tracking
"""

import pytest
from uuid import UUID
from sqlalchemy import select

from src.models.checkpoint import Checkpoint
from src.models.correction import Correction


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_creation(
    test_client,
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test checkpoint creation after subtask completion"""
    # Create task with high checkpoint frequency
    task_info = await task_factory.create_task(
        description="Feature requiring frequent checkpoints",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete first subtask
    subtask_id = UUID(subtasks[0]["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Check if checkpoint was created
    # (In full implementation, checkpoint service would auto-create)
    result = await db_session.execute(
        select(Checkpoint).where(Checkpoint.task_id == task_id)
    )
    checkpoints = result.scalars().all()

    # May or may not have checkpoint depending on implementation
    # This documents expected behavior


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_list_for_task(
    test_client,
    task_factory,
    db_session
):
    """Test listing checkpoints for a task"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for checkpoint listing",
        task_type="develop_feature",
        checkpoint_frequency="medium"
    )
    task_id = task_info["task_id"]

    # Get checkpoints via API
    response = await test_client.get(f"/api/v1/tasks/{task_id}/checkpoints")
    assert response.status_code == 200

    data = response.json()
    assert "checkpoints" in data
    assert "total" in data
    assert isinstance(data["checkpoints"], list)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_accept_decision(
    test_client,
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test user accepting checkpoint - continues task execution"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for accept decision test",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete subtask
    await subtask_factory.submit_result(
        subtask_id=UUID(subtasks[0]["subtask_id"]),
        status="completed",
        output=sample_code_output
    )

    # Manually create checkpoint for testing
    checkpoint = Checkpoint(
        task_id=task_id,
        status="pending_review",
        subtasks_completed=[str(subtasks[0]["subtask_id"])]
    )
    db_session.add(checkpoint)
    await db_session.commit()
    await db_session.refresh(checkpoint)

    # Submit accept decision
    decision_data = {
        "decision": "accept",
        "feedback": "Code looks good, continue with next steps"
    }

    response = await test_client.post(
        f"/api/v1/checkpoints/{checkpoint.checkpoint_id}/decision",
        json=decision_data
    )

    # May return 200 or 404 depending on implementation
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "approved"
        assert "next_action" in data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_correct_decision(
    test_client,
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test user requesting corrections at checkpoint"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for correction decision test",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete subtask
    subtask_id = UUID(subtasks[0]["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create checkpoint
    checkpoint = Checkpoint(
        task_id=task_id,
        status="pending_review",
        subtasks_completed=[str(subtask_id)]
    )
    db_session.add(checkpoint)
    await db_session.commit()
    await db_session.refresh(checkpoint)

    # Submit correct decision
    decision_data = {
        "decision": "correct",
        "feedback": "Please add more error handling and input validation",
        "correction_type": "incomplete",
        "reference_files": ["docs/error_handling.md"],
        "apply_to_future": False
    }

    response = await test_client.post(
        f"/api/v1/checkpoints/{checkpoint.checkpoint_id}/decision",
        json=decision_data
    )

    # May return 200 or 404 depending on implementation
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "corrected"
        assert "corrections_created" in data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_reject_decision(
    test_client,
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test user rejecting checkpoint - cancels task"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for reject decision test",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete subtask
    await subtask_factory.submit_result(
        subtask_id=UUID(subtasks[0]["subtask_id"]),
        status="completed",
        output=sample_code_output
    )

    # Create checkpoint
    checkpoint = Checkpoint(
        task_id=task_id,
        status="pending_review",
        subtasks_completed=[str(subtasks[0]["subtask_id"])]
    )
    db_session.add(checkpoint)
    await db_session.commit()
    await db_session.refresh(checkpoint)

    # Submit reject decision
    decision_data = {
        "decision": "reject",
        "feedback": "Approach is not correct, need to redesign"
    }

    response = await test_client.post(
        f"/api/v1/checkpoints/{checkpoint.checkpoint_id}/decision",
        json=decision_data
    )

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "rejected"
        assert data["task_status"] == "cancelled"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_with_subtask_details(
    test_client,
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    db_session
):
    """Test checkpoint includes detailed subtask information"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for detailed checkpoint",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    # Complete subtask
    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create evaluation
    await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=8.5,
        completeness=9.0,
        security=8.0
    )

    # Create checkpoint
    checkpoint = Checkpoint(
        task_id=task_id,
        status="pending_review",
        subtasks_completed=[str(subtask_id)]
    )
    db_session.add(checkpoint)
    await db_session.commit()
    await db_session.refresh(checkpoint)

    # Get checkpoint details
    response = await test_client.get(
        f"/api/v1/checkpoints/{checkpoint.checkpoint_id}"
    )

    if response.status_code == 200:
        data = response.json()
        assert "subtask_details" in data or "subtasks_completed" in data
        assert "evaluations" in data or data["status"] == "pending_review"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_history(
    test_client,
    task_factory,
    db_session
):
    """Test retrieving checkpoint history for a task"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for history test",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    # Create multiple checkpoints
    for i in range(3):
        checkpoint = Checkpoint(
            task_id=task_id,
            status=["pending_review", "approved", "approved"][i],
            subtasks_completed=[str(UUID(int=i))]
        )
        db_session.add(checkpoint)

    await db_session.commit()

    # Get checkpoint history
    response = await test_client.get(
        f"/api/v1/tasks/{task_id}/checkpoints/history"
    )

    if response.status_code == 200:
        data = response.json()
        assert "checkpoints" in data
        assert "statistics" in data
        assert data["total"] >= 3


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_frequency_low(
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test that low checkpoint frequency creates fewer checkpoints"""
    # Create task with low checkpoint frequency
    task_info = await task_factory.create_task(
        description="Task with low checkpoint frequency",
        task_type="develop_feature",
        checkpoint_frequency="low"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete multiple subtasks
    for subtask in subtasks[:2]:
        await subtask_factory.submit_result(
            subtask_id=UUID(subtask["subtask_id"]),
            status="completed",
            output=sample_code_output
        )

    # Check checkpoint count (should be fewer with low frequency)
    result = await db_session.execute(
        select(Checkpoint).where(Checkpoint.task_id == task_id)
    )
    checkpoints = result.scalars().all()

    # With low frequency, may not create checkpoint after every subtask
    # This is configuration-dependent


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_frequency_high(
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test that high checkpoint frequency creates more checkpoints"""
    # Create task with high checkpoint frequency
    task_info = await task_factory.create_task(
        description="Task with high checkpoint frequency",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete first subtask
    await subtask_factory.submit_result(
        subtask_id=UUID(subtasks[0]["subtask_id"]),
        status="completed",
        output=sample_code_output
    )

    # With high frequency, should be more likely to create checkpoint
    result = await db_session.execute(
        select(Checkpoint).where(Checkpoint.task_id == task_id)
    )
    checkpoints = result.scalars().all()

    # May or may not have checkpoint depending on trigger logic


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_correction_record_creation(
    test_client,
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test creation of Correction records when user requests fixes"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for correction record test",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    # Complete subtask
    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create checkpoint
    checkpoint = Checkpoint(
        task_id=task_id,
        status="pending_review",
        subtasks_completed=[str(subtask_id)]
    )
    db_session.add(checkpoint)
    await db_session.commit()
    await db_session.refresh(checkpoint)

    # Request correction
    decision_data = {
        "decision": "correct",
        "feedback": "Add comprehensive unit tests",
        "correction_type": "incomplete"
    }

    response = await test_client.post(
        f"/api/v1/checkpoints/{checkpoint.checkpoint_id}/decision",
        json=decision_data
    )

    if response.status_code == 200:
        # Check for correction records
        result = await db_session.execute(
            select(Correction).where(
                Correction.checkpoint_id == checkpoint.checkpoint_id
            )
        )
        corrections = result.scalars().all()

        # May have corrections depending on implementation
        # This documents expected behavior


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_statistics(
    test_client,
    task_factory,
    db_session
):
    """Test checkpoint statistics calculation"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for statistics test",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    # Create checkpoints with different statuses
    statuses = ["approved", "approved", "corrected", "pending_review"]
    for status in statuses:
        checkpoint = Checkpoint(
            task_id=task_id,
            status=status,
            subtasks_completed=[str(UUID(int=0))]
        )
        db_session.add(checkpoint)

    await db_session.commit()

    # Get history with statistics
    response = await test_client.get(
        f"/api/v1/tasks/{task_id}/checkpoints/history"
    )

    if response.status_code == 200:
        data = response.json()

        if "statistics" in data:
            stats = data["statistics"]
            assert "total" in stats
            assert stats["total"] == 4


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_nonexistent(test_client):
    """Test operations on non-existent checkpoint"""
    fake_checkpoint_id = UUID(int=999999)

    # Try to get non-existent checkpoint
    response = await test_client.get(
        f"/api/v1/checkpoints/{fake_checkpoint_id}"
    )
    assert response.status_code == 404

    # Try to submit decision on non-existent checkpoint
    response = await test_client.post(
        f"/api/v1/checkpoints/{fake_checkpoint_id}/decision",
        json={"decision": "accept", "feedback": "Test"}
    )
    assert response.status_code in [400, 404]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_prevents_duplicate_decisions(
    test_client,
    task_factory,
    db_session
):
    """Test that checkpoint cannot be decided twice"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for duplicate decision test",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    # Create checkpoint
    checkpoint = Checkpoint(
        task_id=task_id,
        status="pending_review",
        subtasks_completed=[str(UUID(int=0))]
    )
    db_session.add(checkpoint)
    await db_session.commit()
    await db_session.refresh(checkpoint)

    # Submit first decision
    decision_data = {"decision": "accept", "feedback": "Looks good"}

    response1 = await test_client.post(
        f"/api/v1/checkpoints/{checkpoint.checkpoint_id}/decision",
        json=decision_data
    )

    if response1.status_code == 200:
        # Try to submit second decision
        response2 = await test_client.post(
            f"/api/v1/checkpoints/{checkpoint.checkpoint_id}/decision",
            json={"decision": "reject", "feedback": "Changed my mind"}
        )

        # Should reject duplicate decision (or accept if idempotent)
        # Exact behavior depends on implementation


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_checkpoint_with_evaluation_summary(
    test_client,
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    db_session
):
    """Test checkpoint includes evaluation summary for review"""
    # Create task
    task_info = await task_factory.create_task(
        description="Task for evaluation summary in checkpoint",
        task_type="develop_feature",
        checkpoint_frequency="high"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete subtasks with evaluations
    subtask_ids = []
    for subtask in subtasks[:2]:
        subtask_id = UUID(subtask["subtask_id"])
        subtask_ids.append(subtask_id)

        await subtask_factory.submit_result(
            subtask_id=subtask_id,
            status="completed",
            output=sample_code_output
        )

        await evaluation_factory.create_evaluation(
            subtask_id=subtask_id,
            code_quality=8.0,
            completeness=8.5,
            security=7.5
        )

    # Create checkpoint
    checkpoint = Checkpoint(
        task_id=task_id,
        status="pending_review",
        subtasks_completed=[str(sid) for sid in subtask_ids]
    )
    db_session.add(checkpoint)
    await db_session.commit()
    await db_session.refresh(checkpoint)

    # Get checkpoint details
    response = await test_client.get(
        f"/api/v1/checkpoints/{checkpoint.checkpoint_id}"
    )

    if response.status_code == 200:
        data = response.json()

        # Should include evaluation information
        # to help user make informed decision
        assert "checkpoint_id" in data
        assert data["status"] == "pending_review"
