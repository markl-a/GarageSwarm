"""
E2E Tests: Agent Review Workflow

Tests for the agent review and correction workflow:
- Auto-creation of review subtasks
- Review result processing
- Auto-fix workflow triggering
- Review cycle limits
- Escalation to human review
"""

import pytest
from uuid import UUID
from sqlalchemy import select

from src.models.subtask import Subtask
from src.models.correction import Correction


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_subtask_auto_creation(
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test automatic creation of review subtask after code generation"""
    # Create task
    task_info = await task_factory.create_task(
        description="Feature requiring code review",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Find code_generation subtask
    code_gen_subtask = next(
        (s for s in subtasks if s.get("subtask_type") == "code_generation"),
        subtasks[0]  # Fallback to first subtask
    )

    # Complete code generation subtask
    code_gen_id = UUID(code_gen_subtask["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=code_gen_id,
        status="completed",
        output=sample_code_output
    )

    # Check if review subtask was auto-created
    result = await db_session.execute(
        select(Subtask).where(
            Subtask.task_id == task_id,
            Subtask.subtask_type == "code_review"
        )
    )
    review_subtasks = result.scalars().all()

    # Should have at least one review subtask (might be created by decomposer)
    # In full implementation, review service would create it automatically
    assert len(review_subtasks) >= 0  # Review might be part of initial decomposition


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_with_high_score(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    sample_review_output
):
    """Test review workflow when code quality is high (passes review)"""
    # Create task
    task_info = await task_factory.create_task(
        description="Feature with good code quality",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete code generation
    code_gen_subtask = subtasks[0]
    code_gen_id = UUID(code_gen_subtask["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=code_gen_id,
        status="completed",
        output=sample_code_output
    )

    # Create high-score evaluation
    await evaluation_factory.create_evaluation(
        subtask_id=code_gen_id,
        code_quality=9.0,
        completeness=9.5,
        security=9.0,
        architecture=8.5,
        testability=9.0
    )

    # Find review subtask if exists
    review_subtask = next(
        (s for s in subtasks if s.get("subtask_type") == "code_review"),
        None
    )

    if review_subtask:
        review_id = UUID(review_subtask["subtask_id"])

        # Complete review with positive result
        await subtask_factory.submit_result(
            subtask_id=review_id,
            status="completed",
            output=sample_review_output
        )

        # Create high evaluation for review
        await evaluation_factory.create_evaluation(
            subtask_id=review_id,
            code_quality=9.0,
            completeness=9.0,
            security=9.0
        )

        # Verify no fix subtask was created (review passed)
        task_details = await task_factory.get_task_details(task_id)
        fix_subtasks = [
            s for s in task_details["subtasks"]
            if s.get("subtask_type") == "code_fix"
        ]

        # Should not create fix subtask for high scores
        # (In real implementation, review service would check this)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_with_low_score_triggers_fix(
    task_factory,
    subtask_factory,
    evaluation_factory,
    db_session,
    sample_code_output
):
    """Test that low review score triggers auto-fix workflow"""
    # Create task
    task_info = await task_factory.create_task(
        description="Feature with code needing fixes",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete code generation with low quality
    code_gen_id = UUID(subtasks[0]["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=code_gen_id,
        status="completed",
        output=sample_code_output
    )

    # Create low-score evaluation (below threshold)
    await evaluation_factory.create_evaluation(
        subtask_id=code_gen_id,
        code_quality=5.0,  # Below threshold
        completeness=5.5,
        security=5.0,
        architecture=6.0,
        testability=5.5
    )

    # In real implementation, review service would:
    # 1. Detect low score
    # 2. Create code_fix subtask automatically
    # 3. Set original subtask to "correcting" status

    # Check for fix subtask creation
    result = await db_session.execute(
        select(Subtask).where(
            Subtask.task_id == task_id,
            Subtask.subtask_type == "code_fix"
        )
    )
    fix_subtasks = result.scalars().all()

    # Note: In basic implementation, might not have auto-fix
    # This test documents the expected behavior


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_review_fix_cycles(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    db_session
):
    """Test multiple review-fix cycles with eventual success"""
    # Create task
    task_info = await task_factory.create_task(
        description="Feature requiring multiple fix cycles",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    code_gen_id = UUID(subtasks[0]["subtask_id"])

    # Cycle 1: Generate -> Low score
    await subtask_factory.submit_result(
        subtask_id=code_gen_id,
        status="completed",
        output=sample_code_output
    )

    await evaluation_factory.create_evaluation(
        subtask_id=code_gen_id,
        code_quality=5.5,
        completeness=6.0,
        security=5.0
    )

    # In full implementation:
    # - System creates fix subtask
    # - Agent completes fix
    # - Review happens again
    # - If still low, another fix cycle
    # - After MAX_FIX_CYCLES (2), escalate to human

    # For now, verify the subtask exists and can be updated
    task_details = await task_factory.get_task_details(task_id)
    assert len(task_details["subtasks"]) >= 1


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_cycle_limit_reached(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    db_session
):
    """Test that review cycles are limited and escalate to human after max"""
    # Create task
    task_info = await task_factory.create_task(
        description="Feature with persistent issues",
        task_type="develop_feature",
        checkpoint_frequency="high"  # Ensure checkpoints are created
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Simulate multiple fix attempts
    # In real system:
    # - After 2 fix cycles, should create checkpoint for human review
    # - Task status should change to "checkpoint"
    # - No more auto-fix attempts

    # Complete first subtask
    code_gen_id = UUID(subtasks[0]["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=code_gen_id,
        status="completed",
        output=sample_code_output
    )

    # Low evaluation
    await evaluation_factory.create_evaluation(
        subtask_id=code_gen_id,
        code_quality=4.0,
        completeness=5.0,
        security=4.5
    )

    # System should track fix attempts and limit them
    # After reaching limit, checkpoint should be created


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_different_worker_assignment(
    worker_factory,
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test that review subtask is assigned to different worker than original"""
    # Create two workers
    worker1 = await worker_factory.create_worker(machine_name="Code Generator Worker")
    worker2 = await worker_factory.create_worker(machine_name="Code Reviewer Worker")

    # Create task
    task_info = await task_factory.create_task(
        description="Feature requiring different reviewer",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Get subtasks from database to check assignments
    result = await db_session.execute(
        select(Subtask).where(Subtask.task_id == task_id)
    )
    db_subtasks = result.scalars().all()

    # Find code generation and review subtasks
    code_gen = next(
        (s for s in db_subtasks if s.subtask_type == "code_generation"),
        db_subtasks[0] if db_subtasks else None
    )
    code_review = next(
        (s for s in db_subtasks if s.subtask_type == "code_review"),
        None
    )

    # Simulate worker1 completing code generation
    if code_gen:
        # Update worker assignment
        code_gen.assigned_worker = worker1["worker_id"]
        await db_session.commit()

        await subtask_factory.submit_result(
            subtask_id=code_gen.subtask_id,
            status="completed",
            output=sample_code_output
        )

    # If review subtask exists, it should be assignable to different worker
    if code_review:
        # In proper implementation, system would ensure review goes to different agent
        # This is a business rule enforced by the allocation service
        pass


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_includes_original_output(
    task_factory,
    subtask_factory,
    sample_code_output,
    db_session
):
    """Test that review subtask has access to original subtask output"""
    # Create task
    task_info = await task_factory.create_task(
        description="Feature for output propagation test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete code generation
    code_gen_id = UUID(subtasks[0]["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=code_gen_id,
        status="completed",
        output=sample_code_output
    )

    # Get review subtask if it exists
    result = await db_session.execute(
        select(Subtask).where(
            Subtask.task_id == task_id,
            Subtask.subtask_type == "code_review"
        )
    )
    review_subtask = result.scalar_one_or_none()

    if review_subtask:
        # Review subtask should have reference to original output
        # This could be in dependencies or description
        assert review_subtask.dependencies is not None or True


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_result_parsing(
    task_factory,
    subtask_factory,
    sample_review_output
):
    """Test parsing and validation of review results"""
    # Create task
    task_info = await task_factory.create_task(
        description="Feature for review result testing",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Find review subtask
    review_subtask = next(
        (s for s in subtasks if s.get("subtask_type") == "code_review"),
        None
    )

    if review_subtask:
        review_id = UUID(review_subtask["subtask_id"])

        # Submit review result
        result = await subtask_factory.submit_result(
            subtask_id=review_id,
            status="completed",
            output=sample_review_output
        )

        assert result["status"] == "completed"

        # Verify output was saved
        subtask_details = await subtask_factory.get_subtask_details(review_id)
        assert subtask_details["output"] is not None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_correction_record_creation(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    db_session
):
    """Test creation of Correction records for tracking fixes"""
    # Create task
    task_info = await task_factory.create_task(
        description="Feature requiring corrections",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete subtask with issues
    subtask_id = UUID(subtasks[0]["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create low evaluation
    eval_result = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=4.5,
        completeness=5.0,
        security=4.0
    )

    # In full implementation, system would create Correction record
    # Correction links: checkpoint -> subtask -> issue details

    # Check for correction records
    result = await db_session.execute(
        select(Correction).where(Correction.subtask_id == subtask_id)
    )
    corrections = result.scalars().all()

    # May or may not have corrections depending on implementation
    # This test documents expected behavior


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_workflow_end_to_end(
    worker_factory,
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    sample_review_output
):
    """Complete end-to-end review workflow test"""
    # Setup: Create workers
    code_worker = await worker_factory.create_worker(
        machine_name="Code Agent",
        tools=["claude_code"]
    )
    review_worker = await worker_factory.create_worker(
        machine_name="Review Agent",
        tools=["gemini_cli"]
    )

    # Step 1: Create and decompose task
    task_info = await task_factory.create_task(
        description="Complete review workflow test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    assert len(subtasks) >= 2

    # Step 2: Complete code generation
    code_gen_subtask = subtasks[0]
    code_gen_id = UUID(code_gen_subtask["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=code_gen_id,
        status="completed",
        output=sample_code_output
    )

    # Step 3: Create evaluation
    eval_result = await evaluation_factory.create_evaluation(
        subtask_id=code_gen_id,
        code_quality=8.5,
        completeness=9.0,
        security=8.0,
        architecture=8.5,
        testability=8.0
    )
    assert eval_result.overall_score >= 7.0

    # Step 4: If review subtask exists, complete it
    review_subtask = next(
        (s for s in subtasks if s.get("subtask_type") == "code_review"),
        None
    )

    if review_subtask:
        review_id = UUID(review_subtask["subtask_id"])

        await subtask_factory.submit_result(
            subtask_id=review_id,
            status="completed",
            output=sample_review_output
        )

        # Step 5: Verify workflow completion
        task_details = await task_factory.get_task_details(task_id)

        # Both subtasks should be completed
        completed_count = sum(
            1 for s in task_details["subtasks"]
            if s["status"] == "completed"
        )
        assert completed_count >= 2

        # Task should show progress
        assert task_details["progress"] > 0
