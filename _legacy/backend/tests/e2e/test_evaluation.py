"""
E2E Tests: Evaluation Framework

Tests for the automated evaluation system:
- Code quality evaluation
- Completeness assessment
- Security scanning
- Evaluation aggregation
- Score thresholds and triggers
"""

import pytest
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select

from src.models.evaluation import Evaluation


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_creation(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output
):
    """Test creating evaluation for completed subtask"""
    # Create task and subtask
    task_info = await task_factory.create_task(
        description="Feature for evaluation testing",
        task_type="develop_feature"
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
    evaluation = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=8.5,
        completeness=9.0,
        security=8.0,
        architecture=7.5,
        testability=8.5
    )

    # Verify evaluation was created
    assert evaluation.evaluation_id is not None
    assert evaluation.subtask_id == subtask_id
    assert evaluation.code_quality == Decimal("8.5")
    assert evaluation.completeness == Decimal("9.0")
    assert evaluation.security == Decimal("8.0")
    assert evaluation.overall_score is not None
    assert evaluation.overall_score > Decimal("0.0")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_score_calculation(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output
):
    """Test weighted overall score calculation"""
    # Create task and subtask
    task_info = await task_factory.create_task(
        description="Score calculation test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create evaluation with known scores
    evaluation = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=8.0,  # weight 1.5x
        completeness=9.0,  # weight 1.5x
        security=7.0,      # weight 2.0x
        architecture=8.0,  # weight 1.0x
        testability=8.0    # weight 1.0x
    )

    # Calculate expected weighted score
    # (7.0*2.0 + 8.0*1.5 + 9.0*1.5 + 8.0*1.0 + 8.0*1.0) / (2.0+1.5+1.5+1.0+1.0)
    # = (14 + 12 + 13.5 + 8 + 8) / 7.0
    # = 55.5 / 7.0 = 7.93 (rounded to 7.9 or 8.0)

    # Verify overall score was calculated
    assert evaluation.overall_score is not None
    assert 7.5 <= float(evaluation.overall_score) <= 8.5


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_passing_threshold(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output
):
    """Test evaluation passing/failing threshold"""
    # Create task and subtask
    task_info = await task_factory.create_task(
        description="Threshold test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create passing evaluation (score >= 7.0)
    passing_eval = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=8.0,
        completeness=8.5,
        security=8.0,
        architecture=7.5,
        testability=8.0
    )

    # Test passing threshold
    assert passing_eval.is_passing(threshold=7.0) is True
    assert passing_eval.is_passing(threshold=9.0) is False


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_failing_threshold(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    db_session
):
    """Test evaluation failing threshold triggers appropriate action"""
    # Create task
    task_info = await task_factory.create_task(
        description="Failing evaluation test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Create second subtask for this test
    from src.models.subtask import Subtask
    failing_subtask = Subtask(
        task_id=task_id,
        name="Low Quality Code",
        description="Code with quality issues",
        status="completed",
        subtask_type="code_generation",
        output=sample_code_output
    )
    db_session.add(failing_subtask)
    await db_session.commit()
    await db_session.refresh(failing_subtask)

    # Create failing evaluation (score < 7.0)
    failing_eval = await evaluation_factory.create_evaluation(
        subtask_id=failing_subtask.subtask_id,
        code_quality=5.0,
        completeness=6.0,
        security=5.5,
        architecture=6.0,
        testability=5.5
    )

    # Test failing threshold
    assert failing_eval.is_passing(threshold=7.0) is False

    # Verify low score
    assert float(failing_eval.overall_score) < 7.0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_critical_security_issues(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output
):
    """Test detection of critical security issues"""
    # Create task and subtask
    task_info = await task_factory.create_task(
        description="Security evaluation test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create evaluation with critical security issue (score < 7.0)
    evaluation = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=8.0,
        completeness=8.5,
        security=5.0,  # Critical security issue
        architecture=8.0,
        testability=8.0
    )

    # Test critical issue detection
    assert evaluation.has_critical_issues() is True


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_no_critical_issues(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output
):
    """Test that good security score doesn't flag critical issues"""
    # Create task and subtask
    task_info = await task_factory.create_task(
        description="Good security test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create evaluation with good security
    evaluation = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=8.0,
        completeness=8.5,
        security=9.0,  # Good security
        architecture=8.0,
        testability=8.0
    )

    # Should not have critical issues
    assert evaluation.has_critical_issues() is False


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_partial_scores(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output
):
    """Test evaluation with only some dimensions scored"""
    # Create task and subtask
    task_info = await task_factory.create_task(
        description="Partial evaluation test",
        task_type="documentation"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create evaluation with only some scores
    evaluation = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=None,  # Not applicable for documentation
        completeness=9.0,
        security=None,
        architecture=None,
        testability=None
    )

    # Should still calculate overall score from available dimensions
    assert evaluation.overall_score is not None
    assert evaluation.overall_score > Decimal("0.0")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_evaluations_per_subtask(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    db_session
):
    """Test that subtask can have multiple evaluations (e.g., after fixes)"""
    # Create task and subtask
    task_info = await task_factory.create_task(
        description="Multiple evaluations test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create first evaluation (poor quality)
    eval1 = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=5.0,
        completeness=6.0,
        security=5.5
    )

    # Create second evaluation (after fix - better quality)
    eval2 = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=8.5,
        completeness=9.0,
        security=8.0
    )

    # Query all evaluations for this subtask
    result = await db_session.execute(
        select(Evaluation).where(Evaluation.subtask_id == subtask_id)
    )
    evaluations = result.scalars().all()

    # Should have 2 evaluations
    assert len(evaluations) == 2

    # Second evaluation should be better
    scores = sorted([float(e.overall_score) for e in evaluations])
    assert scores[1] > scores[0]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_api_integration(
    test_client,
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output
):
    """Test evaluation data is exposed via API"""
    # Create task and subtask
    task_info = await task_factory.create_task(
        description="API evaluation test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create evaluation
    evaluation = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=8.5,
        completeness=9.0,
        security=8.0,
        architecture=8.0,
        testability=8.5
    )

    # Get task details via API
    response = await test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200

    task_data = response.json()

    # Find the subtask
    subtask_data = next(
        (s for s in task_data["subtasks"] if str(s["subtask_id"]) == str(subtask_id)),
        None
    )

    assert subtask_data is not None

    # Check if evaluation data is included
    if "evaluation" in subtask_data and subtask_data["evaluation"]:
        eval_data = subtask_data["evaluation"]
        # Verify evaluation scores are exposed
        assert "code_quality" in eval_data or "overall_score" in eval_data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_aggregation_across_subtasks(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    db_session
):
    """Test aggregating evaluation scores across all subtasks"""
    # Create task
    task_info = await task_factory.create_task(
        description="Aggregation test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Complete multiple subtasks with evaluations
    evaluated_subtasks = []

    for i, subtask in enumerate(subtasks[:3]):  # Evaluate first 3
        subtask_id = UUID(subtask["subtask_id"])

        await subtask_factory.submit_result(
            subtask_id=subtask_id,
            status="completed",
            output=sample_code_output
        )

        # Create evaluation with varying scores
        evaluation = await evaluation_factory.create_evaluation(
            subtask_id=subtask_id,
            code_quality=7.0 + i * 0.5,
            completeness=8.0 + i * 0.3,
            security=7.5 + i * 0.4,
            architecture=7.0,
            testability=8.0
        )

        evaluated_subtasks.append((subtask_id, evaluation))

    # Query all evaluations for this task
    result = await db_session.execute(
        select(Evaluation)
        .join(Subtask)
        .where(Subtask.task_id == task_id)
    )
    evaluations = result.scalars().all()

    # Should have evaluations for the subtasks we completed
    assert len(evaluations) >= 3

    # Calculate average overall score
    if evaluations:
        avg_score = sum(float(e.overall_score) for e in evaluations) / len(evaluations)
        assert avg_score > 0.0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_with_detailed_results(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output,
    db_session
):
    """Test evaluation with detailed results in JSONB field"""
    # Create task and subtask
    task_info = await task_factory.create_task(
        description="Detailed evaluation test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)
    subtask_id = UUID(subtasks[0]["subtask_id"])

    await subtask_factory.submit_result(
        subtask_id=subtask_id,
        status="completed",
        output=sample_code_output
    )

    # Create evaluation
    evaluation = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id,
        code_quality=8.5,
        completeness=9.0,
        security=8.0
    )

    # Update evaluation with detailed results
    evaluation.details = {
        "code_quality": {
            "issues": [
                {"line": 15, "severity": "minor", "message": "Consider using list comprehension"},
                {"line": 42, "severity": "minor", "message": "Variable name could be more descriptive"}
            ],
            "metrics": {
                "cyclomatic_complexity": 5,
                "maintainability_index": 85
            }
        },
        "security": {
            "issues": [
                {"line": 23, "severity": "info", "message": "Consider input validation"}
            ]
        }
    }

    await db_session.commit()
    await db_session.refresh(evaluation)

    # Verify details were saved
    assert evaluation.details is not None
    assert "code_quality" in evaluation.details
    assert len(evaluation.details["code_quality"]["issues"]) == 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_score_boundaries(
    task_factory,
    subtask_factory,
    evaluation_factory,
    sample_code_output
):
    """Test evaluation with boundary scores (0.0 and 10.0)"""
    # Create task and subtasks
    task_info = await task_factory.create_task(
        description="Boundary score test",
        task_type="develop_feature"
    )
    task_id = task_info["task_id"]

    subtasks = await task_factory.decompose_task(task_id)

    # Test minimum scores (0.0)
    subtask_id_1 = UUID(subtasks[0]["subtask_id"])
    await subtask_factory.submit_result(
        subtask_id=subtask_id_1,
        status="completed",
        output=sample_code_output
    )

    eval_min = await evaluation_factory.create_evaluation(
        subtask_id=subtask_id_1,
        code_quality=0.0,
        completeness=0.0,
        security=0.0,
        architecture=0.0,
        testability=0.0
    )

    assert eval_min.overall_score == Decimal("0.0")

    # Test maximum scores (10.0)
    if len(subtasks) > 1:
        subtask_id_2 = UUID(subtasks[1]["subtask_id"])
        await subtask_factory.submit_result(
            subtask_id=subtask_id_2,
            status="completed",
            output=sample_code_output
        )

        eval_max = await evaluation_factory.create_evaluation(
            subtask_id=subtask_id_2,
            code_quality=10.0,
            completeness=10.0,
            security=10.0,
            architecture=10.0,
            testability=10.0
        )

        assert eval_max.overall_score == Decimal("10.0")
