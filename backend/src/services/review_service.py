"""
Review Service - Agent collaboration and code review workflow

This service implements the agent review mechanism where:
- Agent 1 completes code generation
- Agent 2 reviews the code
- Auto-fix flow triggers if review score is below threshold
- Max 2 review-fix cycles before escalation to human review
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
import json
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from src.models.subtask import Subtask
from src.models.task import Task
from src.models.worker import Worker
from src.services.redis_service import RedisService

logger = structlog.get_logger()


# Review configuration
REVIEW_SCORE_THRESHOLD = 6.0  # Scores below this trigger auto-fix
MAX_FIX_CYCLES = 2  # Maximum review-fix cycles before human escalation
REVIEW_DIMENSIONS = ["syntax", "style", "logic", "security", "readability"]


class ReviewService:
    """
    Service for managing agent code review workflows.

    Implements:
    - Auto-creation of review subtasks after code generation
    - Review result parsing and validation
    - Auto-fix workflow triggering
    - Review cycle tracking and escalation
    """

    def __init__(self, db: AsyncSession, redis_service: RedisService):
        """Initialize ReviewService

        Args:
            db: Database session
            redis_service: Redis service instance
        """
        self.db = db
        self.redis = redis_service

    async def create_review_subtask(
        self,
        original_subtask_id: UUID,
        review_cycle: int = 1
    ) -> Optional[Subtask]:
        """
        Create a review subtask for a completed code generation subtask.

        This is called automatically when a code generation subtask completes.
        The review subtask:
        - Is assigned to a different agent (different worker)
        - Has the original output as input
        - Has subtask_type="code_review"

        Args:
            original_subtask_id: UUID of the completed subtask to review
            review_cycle: Current review cycle number (default: 1)

        Returns:
            Created review subtask or None if creation fails

        Raises:
            ValueError: If original subtask not found or invalid state
        """
        logger.info(
            "Creating review subtask",
            original_subtask_id=str(original_subtask_id),
            review_cycle=review_cycle
        )

        # Get original subtask with relationships
        result = await self.db.execute(
            select(Subtask)
            .options(selectinload(Subtask.task))
            .where(Subtask.subtask_id == original_subtask_id)
        )
        original_subtask = result.scalar_one_or_none()

        if not original_subtask:
            raise ValueError(f"Subtask {original_subtask_id} not found")

        if original_subtask.status != "completed":
            raise ValueError(
                f"Cannot create review for subtask {original_subtask_id} "
                f"with status {original_subtask.status}"
            )

        if not original_subtask.output:
            raise ValueError(
                f"Subtask {original_subtask_id} has no output to review"
            )

        # Check if review already exists
        existing_review = await self._get_review_subtask(original_subtask_id, review_cycle)
        if existing_review:
            logger.warning(
                "Review subtask already exists",
                original_subtask_id=str(original_subtask_id),
                review_subtask_id=str(existing_review.subtask_id)
            )
            return existing_review

        # Prepare review input from original output
        review_input = {
            "original_subtask_id": str(original_subtask_id),
            "original_subtask_name": original_subtask.name,
            "original_description": original_subtask.description,
            "code_output": original_subtask.output,
            "review_cycle": review_cycle,
            "review_dimensions": REVIEW_DIMENSIONS
        }

        # Create review subtask
        review_subtask = Subtask(
            task_id=original_subtask.task_id,
            name=f"Code Review: {original_subtask.name} (Cycle {review_cycle})",
            description=self._generate_review_description(original_subtask, review_cycle),
            status="pending",
            subtask_type="code_review",  # Mark as review task
            progress=0,
            dependencies=[str(original_subtask_id)],  # Depends on original subtask
            recommended_tool=None,  # Will be assigned by allocator
            complexity=2,  # Review is typically moderate complexity
            priority=original_subtask.priority + 10,  # Higher priority than original
            output={"review_input": review_input}  # Store input in output field temporarily
        )

        # Add metadata to track review relationship
        if not review_subtask.output:
            review_subtask.output = {}
        review_subtask.output["metadata"] = {
            "original_subtask_id": str(original_subtask_id),
            "review_cycle": review_cycle,
            "created_at": datetime.utcnow().isoformat()
        }

        self.db.add(review_subtask)
        await self.db.commit()
        await self.db.refresh(review_subtask)

        logger.info(
            "Review subtask created",
            review_subtask_id=str(review_subtask.subtask_id),
            original_subtask_id=str(original_subtask_id)
        )

        return review_subtask

    async def parse_and_store_review_result(
        self,
        review_subtask_id: UUID,
        review_output: Dict[str, Any]
    ) -> Tuple[float, bool]:
        """
        Parse review output, validate, and store results.

        Expected review output format (JSON):
        {
            "score": 7.5,  # Overall score 0-10
            "issues": [
                {
                    "dimension": "syntax",
                    "severity": "high|medium|low",
                    "description": "Issue description",
                    "location": "file:line or general"
                }
            ],
            "suggestions": [
                {
                    "dimension": "style",
                    "description": "Suggestion for improvement"
                }
            ],
            "summary": "Overall review summary"
        }

        Args:
            review_subtask_id: UUID of the review subtask
            review_output: Raw review output to parse

        Returns:
            Tuple of (score, needs_fix)
            - score: Overall review score
            - needs_fix: True if score < threshold and auto-fix should be triggered

        Raises:
            ValueError: If review subtask not found or invalid output format
        """
        logger.info(
            "Parsing review result",
            review_subtask_id=str(review_subtask_id)
        )

        # Get review subtask
        result = await self.db.execute(
            select(Subtask).where(Subtask.subtask_id == review_subtask_id)
        )
        review_subtask = result.scalar_one_or_none()

        if not review_subtask:
            raise ValueError(f"Review subtask {review_subtask_id} not found")

        # Parse review output
        try:
            # Handle if review_output is a string (JSON)
            if isinstance(review_output, str):
                review_data = json.loads(review_output)
            elif isinstance(review_output, dict):
                review_data = review_output
            else:
                raise ValueError(f"Invalid review output type: {type(review_output)}")

            # Validate required fields
            if "score" not in review_data:
                raise ValueError("Review output missing 'score' field")

            score = float(review_data["score"])
            issues = review_data.get("issues", [])
            suggestions = review_data.get("suggestions", [])
            summary = review_data.get("summary", "")

            # Validate score range
            if not 0 <= score <= 10:
                raise ValueError(f"Review score {score} out of range [0-10]")

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(
                "Failed to parse review output",
                review_subtask_id=str(review_subtask_id),
                error=str(e)
            )
            raise ValueError(f"Invalid review output format: {e}")

        # Store parsed results in subtask output
        review_result = {
            "review_completed_at": datetime.utcnow().isoformat(),
            "score": score,
            "issues": issues,
            "suggestions": suggestions,
            "summary": summary,
            "dimensions_checked": REVIEW_DIMENSIONS,
            "threshold": REVIEW_SCORE_THRESHOLD
        }

        # Merge with existing output (keep metadata)
        current_output = review_subtask.output or {}
        current_output["review_result"] = review_result
        review_subtask.output = current_output

        await self.db.commit()

        # Determine if fix is needed
        needs_fix = score < REVIEW_SCORE_THRESHOLD

        logger.info(
            "Review result stored",
            review_subtask_id=str(review_subtask_id),
            score=score,
            needs_fix=needs_fix,
            issues_count=len(issues)
        )

        return score, needs_fix

    async def create_fix_subtask(
        self,
        original_subtask_id: UUID,
        review_subtask_id: UUID,
        review_cycle: int
    ) -> Optional[Subtask]:
        """
        Create a fix subtask when review score is below threshold.

        The fix subtask:
        - Is assigned back to the original agent (same worker if available)
        - Includes original code + review report as input
        - Has subtask_type="code_fix"
        - After completion, triggers re-review (unless max cycles reached)

        Args:
            original_subtask_id: UUID of the original code generation subtask
            review_subtask_id: UUID of the review subtask
            review_cycle: Current review cycle number

        Returns:
            Created fix subtask or None if max cycles reached

        Raises:
            ValueError: If subtasks not found or invalid state
        """
        logger.info(
            "Creating fix subtask",
            original_subtask_id=str(original_subtask_id),
            review_subtask_id=str(review_subtask_id),
            review_cycle=review_cycle
        )

        # Check if max cycles reached
        if review_cycle >= MAX_FIX_CYCLES:
            logger.warning(
                "Max fix cycles reached, escalating to human review",
                original_subtask_id=str(original_subtask_id),
                review_cycle=review_cycle
            )
            await self._escalate_to_human_review(original_subtask_id, review_subtask_id)
            return None

        # Get original and review subtasks
        original_result = await self.db.execute(
            select(Subtask).where(Subtask.subtask_id == original_subtask_id)
        )
        original_subtask = original_result.scalar_one_or_none()

        review_result = await self.db.execute(
            select(Subtask).where(Subtask.subtask_id == review_subtask_id)
        )
        review_subtask = review_result.scalar_one_or_none()

        if not original_subtask or not review_subtask:
            raise ValueError("Original or review subtask not found")

        # Extract review results
        review_data = review_subtask.output.get("review_result", {})

        # Prepare fix input
        fix_input = {
            "original_subtask_id": str(original_subtask_id),
            "review_subtask_id": str(review_subtask_id),
            "original_code": original_subtask.output,
            "review_report": review_data,
            "review_cycle": review_cycle,
            "issues_to_fix": review_data.get("issues", []),
            "suggestions": review_data.get("suggestions", [])
        }

        # Create fix subtask
        fix_subtask = Subtask(
            task_id=original_subtask.task_id,
            name=f"Fix Code: {original_subtask.name} (Cycle {review_cycle})",
            description=self._generate_fix_description(original_subtask, review_data),
            status="pending",
            subtask_type="code_fix",  # Mark as fix task
            progress=0,
            dependencies=[str(review_subtask_id)],  # Depends on review
            recommended_tool=original_subtask.assigned_tool,  # Prefer same tool
            assigned_worker=original_subtask.assigned_worker,  # Try same worker
            complexity=original_subtask.complexity,
            priority=review_subtask.priority + 5,  # Even higher priority
            output={"fix_input": fix_input}
        )

        # Add metadata
        if not fix_subtask.output:
            fix_subtask.output = {}
        fix_subtask.output["metadata"] = {
            "original_subtask_id": str(original_subtask_id),
            "review_subtask_id": str(review_subtask_id),
            "review_cycle": review_cycle,
            "created_at": datetime.utcnow().isoformat()
        }

        self.db.add(fix_subtask)
        await self.db.commit()
        await self.db.refresh(fix_subtask)

        logger.info(
            "Fix subtask created",
            fix_subtask_id=str(fix_subtask.subtask_id),
            review_cycle=review_cycle
        )

        return fix_subtask

    async def handle_fix_completion(
        self,
        fix_subtask_id: UUID
    ) -> Optional[Subtask]:
        """
        Handle completion of a fix subtask and trigger re-review.

        This creates a new review subtask for the fixed code.

        Args:
            fix_subtask_id: UUID of completed fix subtask

        Returns:
            New review subtask or None if max cycles reached
        """
        logger.info(
            "Handling fix completion",
            fix_subtask_id=str(fix_subtask_id)
        )

        # Get fix subtask
        result = await self.db.execute(
            select(Subtask).where(Subtask.subtask_id == fix_subtask_id)
        )
        fix_subtask = result.scalar_one_or_none()

        if not fix_subtask:
            raise ValueError(f"Fix subtask {fix_subtask_id} not found")

        if fix_subtask.status != "completed":
            raise ValueError(
                f"Fix subtask {fix_subtask_id} has status {fix_subtask.status}, "
                "expected 'completed'"
            )

        # Extract metadata
        metadata = fix_subtask.output.get("metadata", {}) if fix_subtask.output else {}
        original_subtask_id = metadata.get("original_subtask_id")
        current_cycle = metadata.get("review_cycle", 1)
        next_cycle = current_cycle + 1

        if not original_subtask_id:
            raise ValueError("Fix subtask missing original_subtask_id metadata")

        # Check if should create re-review
        if next_cycle > MAX_FIX_CYCLES:
            logger.warning(
                "Max fix cycles reached after fix completion",
                fix_subtask_id=str(fix_subtask_id),
                current_cycle=current_cycle
            )
            await self._escalate_to_human_review(UUID(original_subtask_id), fix_subtask_id)
            return None

        # Create re-review subtask for the FIXED code
        # The fix subtask now contains the corrected code in its output
        # We review the fix_subtask's output
        review_subtask = await self.create_review_subtask(
            original_subtask_id=fix_subtask_id,  # Review the fix subtask
            review_cycle=next_cycle
        )

        # Update the review subtask metadata to track back to the original
        if review_subtask:
            if not review_subtask.output:
                review_subtask.output = {}
            if "metadata" not in review_subtask.output:
                review_subtask.output["metadata"] = {}

            # Maintain reference to the very first original subtask
            review_subtask.output["metadata"]["root_original_subtask_id"] = original_subtask_id
            review_subtask.output["metadata"]["immediate_parent_subtask_id"] = str(fix_subtask_id)
            await self.db.commit()

        return review_subtask

    async def get_review_chain(
        self,
        original_subtask_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get the complete review chain for an original subtask.

        Returns all reviews, fixes, and their relationships in chronological order.

        Args:
            original_subtask_id: UUID of the original subtask

        Returns:
            List of dicts with chain information
        """
        # Get all subtasks related to this review chain
        result = await self.db.execute(
            select(Subtask)
            .where(Subtask.task_id == (
                select(Subtask.task_id)
                .where(Subtask.subtask_id == original_subtask_id)
            ))
        )
        all_subtasks = result.scalars().all()

        # Build chain by finding reviews and fixes
        chain = []

        for subtask in all_subtasks:
            # Check if this subtask is part of the review chain
            if subtask.subtask_type not in ("code_review", "code_fix"):
                continue

            metadata = subtask.output.get("metadata", {}) if subtask.output else {}

            # Check if this belongs to the review chain
            # Either directly references the original, or has it as root_original
            original_match = metadata.get("original_subtask_id") == str(original_subtask_id)
            root_match = metadata.get("root_original_subtask_id") == str(original_subtask_id)

            if original_match or root_match:
                review_cycle = metadata.get("review_cycle", 1)

                chain_entry = {
                    "subtask_id": str(subtask.subtask_id),
                    "subtask_type": subtask.subtask_type,
                    "name": subtask.name,
                    "status": subtask.status,
                    "review_cycle": review_cycle,
                    "created_at": subtask.created_at.isoformat() if subtask.created_at else None,
                    "completed_at": subtask.completed_at.isoformat() if subtask.completed_at else None
                }

                # Add type-specific data
                if subtask.subtask_type == "code_review":
                    review_result = subtask.output.get("review_result", {}) if subtask.output else {}
                    chain_entry["score"] = review_result.get("score")
                    chain_entry["issues_count"] = len(review_result.get("issues", []))

                chain.append(chain_entry)

        # Sort by review cycle and created_at
        chain.sort(key=lambda x: (x["review_cycle"], x.get("created_at", "")))

        return chain

    async def _get_review_subtask(
        self,
        original_subtask_id: UUID,
        review_cycle: int
    ) -> Optional[Subtask]:
        """Get existing review subtask for given original subtask and cycle"""
        result = await self.db.execute(
            select(Subtask)
            .where(Subtask.task_id == (
                select(Subtask.task_id)
                .where(Subtask.subtask_id == original_subtask_id)
            ))
            .where(Subtask.subtask_type == "code_review")
        )
        subtasks = result.scalars().all()

        for subtask in subtasks:
            if not subtask.output or "metadata" not in subtask.output:
                continue
            metadata = subtask.output["metadata"]
            if (
                metadata.get("original_subtask_id") == str(original_subtask_id)
                and metadata.get("review_cycle") == review_cycle
            ):
                return subtask

        return None

    async def _escalate_to_human_review(
        self,
        original_subtask_id: UUID,
        last_review_subtask_id: UUID
    ) -> None:
        """
        Escalate to human review when max cycles reached.

        Updates subtask status and adds a note for human intervention.
        """
        logger.info(
            "Escalating to human review",
            original_subtask_id=str(original_subtask_id)
        )

        # Get original subtask
        result = await self.db.execute(
            select(Subtask).where(Subtask.subtask_id == original_subtask_id)
        )
        original_subtask = result.scalar_one_or_none()

        if original_subtask:
            # Add escalation note to output
            if not original_subtask.output:
                original_subtask.output = {}

            original_subtask.output["escalation"] = {
                "escalated_at": datetime.utcnow().isoformat(),
                "reason": f"Max review-fix cycles ({MAX_FIX_CYCLES}) reached",
                "last_review_subtask_id": str(last_review_subtask_id),
                "requires_human_review": True
            }

            # Update status to indicate human review needed
            original_subtask.status = "correcting"  # Use existing status

            await self.db.commit()

            logger.info(
                "Subtask escalated to human review",
                original_subtask_id=str(original_subtask_id)
            )

    def _generate_review_description(
        self,
        original_subtask: Subtask,
        review_cycle: int
    ) -> str:
        """Generate description for review subtask"""
        return f"""Review the code generated for: {original_subtask.name}

Original Description: {original_subtask.description}

Review Cycle: {review_cycle}

Review Dimensions:
- Syntax: Check for syntax errors and language best practices
- Style: Evaluate code style, formatting, and naming conventions
- Logic: Verify logical correctness and algorithm efficiency
- Security: Identify security vulnerabilities and risks
- Readability: Assess code clarity and maintainability

Provide a structured review with:
1. Overall score (0-10)
2. Issues found with severity levels
3. Suggestions for improvement
4. Summary of findings
"""

    def _generate_fix_description(
        self,
        original_subtask: Subtask,
        review_data: Dict[str, Any]
    ) -> str:
        """Generate description for fix subtask"""
        score = review_data.get("score", 0)
        issues = review_data.get("issues", [])

        issues_text = "\n".join([
            f"- [{issue.get('severity', 'medium')}] {issue.get('description', 'N/A')}"
            for issue in issues[:5]  # Limit to first 5 issues
        ])

        return f"""Fix the code based on review feedback for: {original_subtask.name}

Review Score: {score}/{REVIEW_SCORE_THRESHOLD} (threshold)

Critical Issues to Address:
{issues_text}

Original Task: {original_subtask.description}

Requirements:
- Address all high-severity issues
- Implement suggested improvements
- Maintain original functionality
- Ensure code quality meets review threshold
"""

    def get_review_config(self) -> Dict[str, Any]:
        """Get current review configuration"""
        return {
            "score_threshold": REVIEW_SCORE_THRESHOLD,
            "max_fix_cycles": MAX_FIX_CYCLES,
            "review_dimensions": REVIEW_DIMENSIONS
        }
