"""
Evaluations API

Endpoints for code evaluation and quality assessment.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload
from decimal import Decimal
import structlog

from src.dependencies import get_db
from src.auth.dependencies import require_auth
from src.models.user import User
from src.models.subtask import Subtask
from src.models.evaluation import Evaluation
from src.schemas.evaluation import (
    EvaluationRequest,
    EvaluationReportResponse,
    SubtaskEvaluationResponse,
    EvaluationListResponse,
    EvaluationStatsResponse,
    WeightsConfigRequest,
    WeightsConfigResponse,
    ComponentScore,
    EvaluationSummary,
    QualityGrade
)
from src.evaluators.aggregator import EvaluationAggregator

router = APIRouter()
logger = structlog.get_logger()


@lru_cache(maxsize=1)
def get_aggregator() -> EvaluationAggregator:
    """
    Dependency injection for EvaluationAggregator (singleton pattern).

    Uses lru_cache to ensure only one instance is created and reused.
    This is thread-safe and avoids global mutable state.
    """
    return EvaluationAggregator()


@router.post(
    "/evaluate",
    response_model=EvaluationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Code",
    description="Evaluate code quality, completeness, and security"
)
async def evaluate_code(
    request: EvaluationRequest,
    current_user: User = Depends(require_auth)
):
    """
    Evaluate code using multiple evaluators.

    This endpoint runs comprehensive code evaluation including:
    - Code quality (syntax, linting, complexity, documentation)
    - Completeness (requirement coverage, error handling, tests)
    - Security (vulnerabilities, hardcoded secrets, unsafe functions)

    **Request body:**
    - code: Source code to evaluate
    - language: Programming language (default: python)
    - description: Task/subtask description
    - requirements: List of explicit requirements
    - context: Additional context information

    **Response:**
    - overall_score: Weighted overall score (0-10)
    - quality_grade: Quality grade (excellent/good/acceptable/poor/fail)
    - component_scores: Individual evaluator scores
    - detailed_results: Detailed breakdown from each evaluator
    - all_issues: All issues sorted by severity
    - all_suggestions: All improvement suggestions
    - summary: Human-readable summary
    """
    try:
        aggregator = get_aggregator()

        # Build context from request
        context = {
            "language": request.language,
            "description": request.description or "",
            "requirements": request.requirements,
            **request.context
        }

        # Run evaluation
        report = await aggregator.evaluate_all(request.code, context)

        # Convert to response schema
        return EvaluationReportResponse(
            overall_score=report["overall_score"],
            quality_grade=QualityGrade(report["quality_grade"]),
            component_scores=report["component_scores"],
            weights=report["weights"],
            detailed_results={
                name: ComponentScore(
                    score=details["score"],
                    weight=report["weights"].get(name, 0),
                    details=details["details"],
                    issues=details["issues"],
                    suggestions=details["suggestions"]
                )
                for name, details in report["detailed_results"].items()
            },
            all_issues=report["all_issues"],
            all_suggestions=report["all_suggestions"],
            summary=EvaluationSummary(**report["summary"])
        )

    except Exception as e:
        logger.error("Code evaluation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )


@router.post(
    "/subtasks/{subtask_id}/evaluate",
    response_model=SubtaskEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Subtask",
    description="Evaluate a subtask's code and store results in database"
)
async def evaluate_subtask(
    subtask_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Evaluate a completed subtask and store results.

    This endpoint:
    1. Retrieves the subtask and its code
    2. Runs comprehensive evaluation
    3. Stores results in the evaluations table
    4. Returns the evaluation record

    **Path parameters:**
    - subtask_id: UUID of the subtask to evaluate

    **Response:**
    - Evaluation record with all scores and details

    **Requirements:**
    - Subtask must exist
    - Subtask must have output/code to evaluate
    """
    try:
        # Get subtask
        result = await db.execute(
            select(Subtask)
            .where(Subtask.subtask_id == subtask_id)
            .options(selectinload(Subtask.task))
        )
        subtask = result.scalar_one_or_none()

        if not subtask:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subtask {subtask_id} not found"
            )

        # Extract code from subtask output
        if not subtask.output:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subtask has no output to evaluate"
            )

        code = subtask.output.get("code") or subtask.output.get("text") or ""
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No code found in subtask output"
            )

        # Build context
        context = {
            "language": "python",  # Could be extracted from subtask or task
            "description": subtask.description,
            "requirements": [],  # Could be extracted from description
            "task_id": str(subtask.task_id),
            "subtask_id": str(subtask_id)
        }

        # Run evaluation
        aggregator = get_aggregator()
        report = await aggregator.evaluate_all(code, context)

        # Create evaluation record
        evaluation = Evaluation(
            subtask_id=subtask_id,
            code_quality=Decimal(str(report["component_scores"].get("code_quality"))),
            completeness=Decimal(str(report["component_scores"].get("completeness"))),
            security=Decimal(str(report["component_scores"].get("security"))),
            overall_score=Decimal(str(report["overall_score"])),
            details=report  # Store full report
        )

        db.add(evaluation)
        await db.commit()
        await db.refresh(evaluation)

        logger.info(
            "Subtask evaluated",
            subtask_id=str(subtask_id),
            overall_score=float(evaluation.overall_score),
            grade=report["quality_grade"]
        )

        return SubtaskEvaluationResponse(
            evaluation_id=evaluation.evaluation_id,
            subtask_id=evaluation.subtask_id,
            code_quality=float(evaluation.code_quality) if evaluation.code_quality else None,
            completeness=float(evaluation.completeness) if evaluation.completeness else None,
            security=float(evaluation.security) if evaluation.security else None,
            architecture=float(evaluation.architecture) if evaluation.architecture else None,
            testability=float(evaluation.testability) if evaluation.testability else None,
            overall_score=float(evaluation.overall_score),
            details=evaluation.details,
            evaluated_at=evaluation.evaluated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Subtask evaluation failed",
            subtask_id=str(subtask_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate subtask: {str(e)}"
        )


@router.get(
    "/subtasks/{subtask_id}/evaluation",
    response_model=SubtaskEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Subtask Evaluation",
    description="Retrieve evaluation results for a subtask"
)
async def get_subtask_evaluation(
    subtask_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get the most recent evaluation for a subtask.

    **Path parameters:**
    - subtask_id: UUID of the subtask

    **Response:**
    - Evaluation record with all scores and details
    - Returns 404 if no evaluation found
    """
    try:
        # Get most recent evaluation for subtask
        result = await db.execute(
            select(Evaluation)
            .where(Evaluation.subtask_id == subtask_id)
            .order_by(Evaluation.evaluated_at.desc())
            .limit(1)
        )
        evaluation = result.scalar_one_or_none()

        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No evaluation found for subtask {subtask_id}"
            )

        return SubtaskEvaluationResponse(
            evaluation_id=evaluation.evaluation_id,
            subtask_id=evaluation.subtask_id,
            code_quality=float(evaluation.code_quality) if evaluation.code_quality else None,
            completeness=float(evaluation.completeness) if evaluation.completeness else None,
            security=float(evaluation.security) if evaluation.security else None,
            architecture=float(evaluation.architecture) if evaluation.architecture else None,
            testability=float(evaluation.testability) if evaluation.testability else None,
            overall_score=float(evaluation.overall_score),
            details=evaluation.details,
            evaluated_at=evaluation.evaluated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Get subtask evaluation failed",
            subtask_id=str(subtask_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation: {str(e)}"
        )


@router.get(
    "/subtasks/{subtask_id}/evaluations",
    response_model=EvaluationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Subtask Evaluations",
    description="List all evaluations for a subtask"
)
async def list_subtask_evaluations(
    subtask_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    List all evaluation records for a subtask.

    **Path parameters:**
    - subtask_id: UUID of the subtask

    **Response:**
    - List of all evaluations for the subtask (newest first)
    """
    try:
        # Get all evaluations for subtask
        result = await db.execute(
            select(Evaluation)
            .where(Evaluation.subtask_id == subtask_id)
            .order_by(Evaluation.evaluated_at.desc())
        )
        evaluations = result.scalars().all()

        evaluation_responses = [
            SubtaskEvaluationResponse(
                evaluation_id=evaluation.evaluation_id,
                subtask_id=evaluation.subtask_id,
                code_quality=float(evaluation.code_quality) if evaluation.code_quality else None,
                completeness=float(evaluation.completeness) if evaluation.completeness else None,
                security=float(evaluation.security) if evaluation.security else None,
                architecture=float(evaluation.architecture) if evaluation.architecture else None,
                testability=float(evaluation.testability) if evaluation.testability else None,
                overall_score=float(evaluation.overall_score),
                details=evaluation.details,
                evaluated_at=evaluation.evaluated_at
            )
            for evaluation in evaluations
        ]

        return EvaluationListResponse(
            evaluations=evaluation_responses,
            total=len(evaluation_responses)
        )

    except Exception as e:
        logger.error(
            "List subtask evaluations failed",
            subtask_id=str(subtask_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list evaluations: {str(e)}"
        )


@router.get(
    "/evaluations/stats",
    response_model=EvaluationStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Evaluation Statistics",
    description="Get overall evaluation statistics"
)
async def get_evaluation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get evaluation statistics across all subtasks.

    **Response:**
    - total_evaluations: Total number of evaluations
    - average_score: Average overall score
    - grade_distribution: Count of evaluations by quality grade
    - component_averages: Average scores for each component
    """
    try:
        # Get total count and averages
        result = await db.execute(
            select(
                func.count(Evaluation.evaluation_id).label("total"),
                func.avg(Evaluation.overall_score).label("avg_overall"),
                func.avg(Evaluation.code_quality).label("avg_code_quality"),
                func.avg(Evaluation.completeness).label("avg_completeness"),
                func.avg(Evaluation.security).label("avg_security")
            )
        )
        stats = result.one()

        # Calculate grade distribution
        grade_result = await db.execute(
            select(
                case(
                    (Evaluation.overall_score >= 9.0, "excellent"),
                    (Evaluation.overall_score >= 7.0, "good"),
                    (Evaluation.overall_score >= 5.0, "acceptable"),
                    (Evaluation.overall_score >= 3.0, "poor"),
                    else_="fail"
                ).label("grade"),
                func.count().label("count")
            )
            .group_by("grade")
        )
        grade_dist = {row.grade: row.count for row in grade_result}

        # Fill in missing grades with 0
        for grade in ["excellent", "good", "acceptable", "poor", "fail"]:
            if grade not in grade_dist:
                grade_dist[grade] = 0

        return EvaluationStatsResponse(
            total_evaluations=stats.total or 0,
            average_score=float(stats.avg_overall) if stats.avg_overall else 0.0,
            grade_distribution=grade_dist,
            component_averages={
                "code_quality": float(stats.avg_code_quality) if stats.avg_code_quality else 0.0,
                "completeness": float(stats.avg_completeness) if stats.avg_completeness else 0.0,
                "security": float(stats.avg_security) if stats.avg_security else 0.0
            }
        )

    except Exception as e:
        logger.error("Get evaluation stats failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation stats: {str(e)}"
        )


@router.get(
    "/config/weights",
    response_model=WeightsConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Weights Configuration",
    description="Get current evaluation weights configuration"
)
async def get_weights_config(
    current_user: User = Depends(require_auth)
):
    """
    Get the current weights configuration for evaluation aggregation.

    **Response:**
    - weights: Current weight configuration
    - message: Response message
    """
    try:
        aggregator = get_aggregator()
        weights = aggregator.get_weights()

        return WeightsConfigResponse(
            weights=weights,
            message="Current weights configuration"
        )

    except Exception as e:
        logger.error("Get weights config failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get weights: {str(e)}"
        )


@router.put(
    "/config/weights",
    response_model=WeightsConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Weights Configuration",
    description="Update evaluation weights configuration"
)
async def update_weights_config(
    request: WeightsConfigRequest,
    current_user: User = Depends(require_auth)
):
    """
    Update the weights configuration for evaluation aggregation.

    The weights must sum to approximately 1.0. If they don't,
    they will be automatically normalized.

    **Request body:**
    - code_quality: Weight for code quality evaluator
    - completeness: Weight for completeness evaluator
    - security: Weight for security evaluator
    - reserved: Reserved weight for future evaluators

    **Response:**
    - weights: Updated weight configuration
    - message: Response message
    """
    try:
        aggregator = get_aggregator()

        new_weights = {
            "code_quality": request.code_quality,
            "completeness": request.completeness,
            "security": request.security,
            "reserved": request.reserved
        }

        aggregator.update_weights(new_weights)

        logger.info("Weights configuration updated", weights=new_weights)

        return WeightsConfigResponse(
            weights=aggregator.get_weights(),
            message="Weights updated successfully"
        )

    except Exception as e:
        logger.error("Update weights config failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update weights: {str(e)}"
        )
