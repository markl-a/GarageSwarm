"""
Unit tests for ReviewService

Tests the agent collaboration and code review workflow including:
- Review subtask creation
- Review result parsing and storage
- Fix subtask creation
- Auto-fix flow with cycle limits
- Review chain tracking
"""

import pytest
import pytest_asyncio
import json
from uuid import uuid4
from datetime import datetime
from sqlalchemy import select

from src.services.review_service import ReviewService, REVIEW_SCORE_THRESHOLD, MAX_FIX_CYCLES
from src.models.subtask import Subtask
from src.models.task import Task


@pytest_asyncio.fixture
async def sample_task(db_session):
    """Create a sample task for testing"""
    task = Task(
        description="Test task for review workflow",
        status="in_progress",
        progress=50,
        checkpoint_frequency="medium",
        privacy_level="normal"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def sample_completed_subtask(db_session, sample_task):
    """Create a completed subtask with output"""
    subtask = Subtask(
        task_id=sample_task.task_id,
        name="Generate user authentication module",
        description="Create authentication module with JWT tokens",
        status="completed",
        subtask_type="code_generation",
        progress=100,
        complexity=3,
        priority=5,
        output={
            "text": "Authentication module implementation",
            "files": [
                {"path": "auth/jwt_handler.py", "content": "# JWT implementation"},
                {"path": "auth/middleware.py", "content": "# Auth middleware"}
            ],
            "usage": {"tokens": 1500}
        }
    )
    db_session.add(subtask)
    await db_session.commit()
    await db_session.refresh(subtask)
    return subtask


@pytest.mark.asyncio
class TestReviewSubtaskCreation:
    """Test review subtask creation workflow"""

    async def test_create_review_subtask_success(self, db_session, mock_redis_service, sample_completed_subtask):
        """Test successful creation of review subtask"""
        service = ReviewService(db_session, mock_redis_service)

        # Create review subtask
        review_subtask = await service.create_review_subtask(
            original_subtask_id=sample_completed_subtask.subtask_id,
            review_cycle=1
        )

        assert review_subtask is not None
        assert review_subtask.subtask_type == "code_review"
        assert review_subtask.status == "pending"
        assert review_subtask.complexity == 2
        assert review_subtask.priority == sample_completed_subtask.priority + 10
        assert str(sample_completed_subtask.subtask_id) in review_subtask.dependencies

        # Check metadata
        metadata = review_subtask.output["metadata"]
        assert metadata["original_subtask_id"] == str(sample_completed_subtask.subtask_id)
        assert metadata["review_cycle"] == 1

        # Check review input
        review_input = review_subtask.output["review_input"]
        assert review_input["original_subtask_id"] == str(sample_completed_subtask.subtask_id)
        assert review_input["code_output"] == sample_completed_subtask.output

    async def test_create_review_subtask_not_completed(self, db_session, mock_redis_service, sample_task):
        """Test that review creation fails for non-completed subtask"""
        subtask = Subtask(
            task_id=sample_task.task_id,
            name="In progress task",
            description="Still working",
            status="in_progress",
            subtask_type="code_generation"
        )
        db_session.add(subtask)
        await db_session.commit()
        await db_session.refresh(subtask)

        service = ReviewService(db_session, mock_redis_service)

        with pytest.raises(ValueError, match="Cannot create review"):
            await service.create_review_subtask(subtask.subtask_id)

    async def test_create_review_subtask_no_output(self, db_session, mock_redis_service, sample_task):
        """Test that review creation fails when subtask has no output"""
        subtask = Subtask(
            task_id=sample_task.task_id,
            name="Completed but empty",
            description="No output",
            status="completed",
            subtask_type="code_generation",
            output=None
        )
        db_session.add(subtask)
        await db_session.commit()
        await db_session.refresh(subtask)

        service = ReviewService(db_session, mock_redis_service)

        with pytest.raises(ValueError, match="has no output"):
            await service.create_review_subtask(subtask.subtask_id)

    async def test_create_review_subtask_duplicate(self, db_session, mock_redis_service, sample_completed_subtask):
        """Test that creating duplicate review returns existing review"""
        service = ReviewService(db_session, mock_redis_service)

        # Create first review
        review1 = await service.create_review_subtask(
            original_subtask_id=sample_completed_subtask.subtask_id,
            review_cycle=1
        )

        # Try to create duplicate
        review2 = await service.create_review_subtask(
            original_subtask_id=sample_completed_subtask.subtask_id,
            review_cycle=1
        )

        assert review2.subtask_id == review1.subtask_id


@pytest.mark.asyncio
class TestReviewResultParsing:
    """Test review result parsing and storage"""

    async def test_parse_valid_json_review(self, db_session, mock_redis_service, sample_task):
        """Test parsing valid JSON review output"""
        review_subtask = Subtask(
            task_id=sample_task.task_id,
            name="Code Review",
            description="Review task",
            status="completed",
            subtask_type="code_review",
            output={"metadata": {}}
        )
        db_session.add(review_subtask)
        await db_session.commit()
        await db_session.refresh(review_subtask)

        service = ReviewService(db_session, mock_redis_service)

        review_output = {
            "score": 7.5,
            "issues": [
                {
                    "dimension": "security",
                    "severity": "high",
                    "description": "Hardcoded credentials found",
                    "location": "auth/config.py:15"
                }
            ],
            "suggestions": [
                {
                    "dimension": "style",
                    "description": "Use type hints for function parameters"
                }
            ],
            "summary": "Good implementation with minor security issue"
        }

        score, needs_fix = await service.parse_and_store_review_result(
            review_subtask_id=review_subtask.subtask_id,
            review_output=review_output
        )

        assert score == 7.5
        assert needs_fix is False  # 7.5 >= 6.0 threshold

        # Refresh and check stored data - need to query again since output is updated
        result = await db_session.execute(
            select(Subtask).where(Subtask.subtask_id == review_subtask.subtask_id)
        )
        refreshed_subtask = result.scalar_one()
        assert refreshed_subtask.output is not None
        assert "review_result" in refreshed_subtask.output
        review_result = refreshed_subtask.output["review_result"]
        assert review_result["score"] == 7.5
        assert len(review_result["issues"]) == 1
        assert len(review_result["suggestions"]) == 1

    async def test_parse_json_string_review(self, db_session, mock_redis_service, sample_task):
        """Test parsing review output as JSON string"""
        review_subtask = Subtask(
            task_id=sample_task.task_id,
            name="Code Review",
            description="Review task",
            status="completed",
            subtask_type="code_review",
            output={"metadata": {}}
        )
        db_session.add(review_subtask)
        await db_session.commit()
        await db_session.refresh(review_subtask)

        service = ReviewService(db_session, mock_redis_service)

        review_json = json.dumps({
            "score": 5.5,
            "issues": [],
            "suggestions": [],
            "summary": "Needs improvement"
        })

        score, needs_fix = await service.parse_and_store_review_result(
            review_subtask_id=review_subtask.subtask_id,
            review_output=review_json
        )

        assert score == 5.5
        assert needs_fix is True  # 5.5 < 6.0 threshold

    async def test_parse_review_missing_score(self, db_session, mock_redis_service, sample_task):
        """Test that parsing fails when score is missing"""
        review_subtask = Subtask(
            task_id=sample_task.task_id,
            name="Code Review",
            description="Review task",
            status="completed",
            subtask_type="code_review",
            output={"metadata": {}}
        )
        db_session.add(review_subtask)
        await db_session.commit()
        await db_session.refresh(review_subtask)

        service = ReviewService(db_session, mock_redis_service)

        review_output = {
            "issues": [],
            "suggestions": [],
            "summary": "Missing score"
        }

        with pytest.raises(ValueError, match="missing 'score' field"):
            await service.parse_and_store_review_result(
                review_subtask_id=review_subtask.subtask_id,
                review_output=review_output
            )

    async def test_parse_review_invalid_score_range(self, db_session, mock_redis_service, sample_task):
        """Test that parsing fails when score is out of range"""
        review_subtask = Subtask(
            task_id=sample_task.task_id,
            name="Code Review",
            description="Review task",
            status="completed",
            subtask_type="code_review",
            output={"metadata": {}}
        )
        db_session.add(review_subtask)
        await db_session.commit()
        await db_session.refresh(review_subtask)

        service = ReviewService(db_session, mock_redis_service)

        review_output = {
            "score": 15.0,  # Out of range
            "issues": [],
            "suggestions": [],
            "summary": "Invalid score"
        }

        with pytest.raises(ValueError, match="out of range"):
            await service.parse_and_store_review_result(
                review_subtask_id=review_subtask.subtask_id,
                review_output=review_output
            )


@pytest.mark.asyncio
class TestFixSubtaskCreation:
    """Test fix subtask creation and auto-fix flow"""

    async def test_create_fix_subtask_success(self, db_session, mock_redis_service, sample_task):
        """Test successful creation of fix subtask"""
        # Create original and review subtasks
        original = Subtask(
            task_id=sample_task.task_id,
            name="Original code",
            description="Original implementation",
            status="completed",
            subtask_type="code_generation",
            assigned_tool="claude_code",
            output={"text": "Original code here"}
        )
        db_session.add(original)
        await db_session.commit()
        await db_session.refresh(original)

        review = Subtask(
            task_id=sample_task.task_id,
            name="Code Review",
            description="Review",
            status="completed",
            subtask_type="code_review",
            priority=15,
            output={
                "metadata": {
                    "original_subtask_id": str(original.subtask_id),
                    "review_cycle": 1
                },
                "review_result": {
                    "score": 4.5,
                    "issues": [
                        {"severity": "high", "description": "Security flaw"}
                    ],
                    "suggestions": []
                }
            }
        )
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        service = ReviewService(db_session, mock_redis_service)

        fix_subtask = await service.create_fix_subtask(
            original_subtask_id=original.subtask_id,
            review_subtask_id=review.subtask_id,
            review_cycle=1
        )

        assert fix_subtask is not None
        assert fix_subtask.subtask_type == "code_fix"
        assert fix_subtask.status == "pending"
        assert fix_subtask.recommended_tool == "claude_code"
        assert fix_subtask.priority == review.priority + 5
        assert str(review.subtask_id) in fix_subtask.dependencies

        # Check metadata
        metadata = fix_subtask.output["metadata"]
        assert metadata["original_subtask_id"] == str(original.subtask_id)
        assert metadata["review_cycle"] == 1

    async def test_create_fix_subtask_max_cycles_reached(self, db_session, mock_redis_service, sample_task):
        """Test that fix subtask is not created when max cycles reached"""
        original = Subtask(
            task_id=sample_task.task_id,
            name="Original code",
            description="Original implementation",
            status="completed",
            subtask_type="code_generation",
            output={"text": "Code", "escalation": None}
        )
        db_session.add(original)
        await db_session.commit()
        await db_session.refresh(original)

        review = Subtask(
            task_id=sample_task.task_id,
            name="Code Review",
            description="Review",
            status="completed",
            subtask_type="code_review",
            output={
                "metadata": {},
                "review_result": {"score": 4.5, "issues": []}
            }
        )
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        service = ReviewService(db_session, mock_redis_service)

        # Try to create fix at max cycle
        fix_subtask = await service.create_fix_subtask(
            original_subtask_id=original.subtask_id,
            review_subtask_id=review.subtask_id,
            review_cycle=MAX_FIX_CYCLES
        )

        assert fix_subtask is None

        # Check that original was escalated - query again to get updated data
        result = await db_session.execute(
            select(Subtask).where(Subtask.subtask_id == original.subtask_id)
        )
        refreshed_original = result.scalar_one()
        assert refreshed_original.output is not None
        assert "escalation" in refreshed_original.output
        assert refreshed_original.output["escalation"]["requires_human_review"] is True

    async def test_handle_fix_completion_creates_rereview(self, db_session, mock_redis_service, sample_task):
        """Test that fix completion triggers re-review"""
        # Create fix subtask
        fix = Subtask(
            task_id=sample_task.task_id,
            name="Fix code",
            description="Fix issues",
            status="completed",
            subtask_type="code_fix",
            output={
                "metadata": {
                    "original_subtask_id": str(uuid4()),
                    "review_cycle": 1
                },
                "text": "Fixed code"
            }
        )
        db_session.add(fix)
        await db_session.commit()
        await db_session.refresh(fix)

        service = ReviewService(db_session, mock_redis_service)

        # Handle fix completion
        rereview = await service.handle_fix_completion(fix.subtask_id)

        assert rereview is not None
        assert rereview.subtask_type == "code_review"
        assert rereview.output["metadata"]["review_cycle"] == 2

    async def test_handle_fix_completion_max_cycles(self, db_session, mock_redis_service, sample_task):
        """Test that fix completion at max cycles escalates"""
        original = Subtask(
            task_id=sample_task.task_id,
            name="Original",
            description="Original",
            status="completed",
            subtask_type="code_generation",
            output={"text": "Code"}
        )
        db_session.add(original)
        await db_session.commit()
        await db_session.refresh(original)

        fix = Subtask(
            task_id=sample_task.task_id,
            name="Fix code",
            description="Fix issues",
            status="completed",
            subtask_type="code_fix",
            output={
                "metadata": {
                    "original_subtask_id": str(original.subtask_id),
                    "review_cycle": MAX_FIX_CYCLES
                },
                "text": "Fixed code"
            }
        )
        db_session.add(fix)
        await db_session.commit()
        await db_session.refresh(fix)

        service = ReviewService(db_session, mock_redis_service)

        rereview = await service.handle_fix_completion(fix.subtask_id)

        assert rereview is None

        # Check escalation - query again to get updated data
        result = await db_session.execute(
            select(Subtask).where(Subtask.subtask_id == original.subtask_id)
        )
        refreshed_original = result.scalar_one()
        assert "escalation" in refreshed_original.output


@pytest.mark.asyncio
class TestReviewChain:
    """Test review chain tracking"""

    async def test_get_review_chain(self, db_session, mock_redis_service, sample_task):
        """Test getting complete review chain"""
        # Create original subtask
        original = Subtask(
            task_id=sample_task.task_id,
            name="Original code",
            description="Original",
            status="completed",
            subtask_type="code_generation",
            output={"text": "Code"}
        )
        db_session.add(original)
        await db_session.commit()
        await db_session.refresh(original)

        # Create review cycle 1
        review1 = Subtask(
            task_id=sample_task.task_id,
            name="Review 1",
            description="First review",
            status="completed",
            subtask_type="code_review",
            output={
                "metadata": {
                    "original_subtask_id": str(original.subtask_id),
                    "review_cycle": 1
                },
                "review_result": {
                    "score": 5.0,
                    "issues": [{"description": "Issue 1"}]
                }
            }
        )
        db_session.add(review1)

        # Create fix cycle 1
        fix1 = Subtask(
            task_id=sample_task.task_id,
            name="Fix 1",
            description="First fix",
            status="completed",
            subtask_type="code_fix",
            output={
                "metadata": {
                    "original_subtask_id": str(original.subtask_id),
                    "review_cycle": 1
                }
            }
        )
        db_session.add(fix1)

        await db_session.commit()

        service = ReviewService(db_session, mock_redis_service)

        chain = await service.get_review_chain(original.subtask_id)

        assert len(chain) == 2
        assert chain[0]["subtask_type"] == "code_review"
        assert chain[0]["review_cycle"] == 1
        assert chain[0]["score"] == 5.0
        assert chain[1]["subtask_type"] == "code_fix"


@pytest.mark.asyncio
class TestReviewConfig:
    """Test review configuration"""

    async def test_get_review_config(self, db_session, mock_redis_service):
        """Test getting review configuration"""
        service = ReviewService(db_session, mock_redis_service)
        config = service.get_review_config()

        assert config["score_threshold"] == REVIEW_SCORE_THRESHOLD
        assert config["max_fix_cycles"] == MAX_FIX_CYCLES
        assert "review_dimensions" in config
        assert len(config["review_dimensions"]) == 5
