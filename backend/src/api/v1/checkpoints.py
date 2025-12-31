"""
Checkpoints API

Checkpoint management endpoints for human review and correction system.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.dependencies import get_db, get_redis_service
from src.auth.dependencies import require_auth
from src.models.user import User
from src.services.checkpoint_service import CheckpointService
from src.services.redis_service import RedisService
from src.schemas.checkpoint import (
    CheckpointResponse,
    CheckpointListResponse,
    CheckpointDecisionRequest,
    CheckpointDecisionResponse,
    CheckpointHistoryResponse,
    CheckpointHistoryItem,
    CheckpointStatus,
    UserDecision,
    SubtaskInfo,
    EvaluationInfo,
    RollbackRequest,
    RollbackResponse
)

router = APIRouter()
logger = structlog.get_logger()


async def get_checkpoint_service(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
) -> CheckpointService:
    """Dependency to get CheckpointService instance"""
    return CheckpointService(db, redis_service)


@router.get(
    "/tasks/{task_id}/checkpoints",
    response_model=CheckpointListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Task Checkpoints",
    description="Get all checkpoints for a specific task"
)
async def list_task_checkpoints(
    task_id: UUID,
    checkpoint_service: CheckpointService = Depends(get_checkpoint_service),
    current_user: User = Depends(require_auth)
):
    """
    List all checkpoints for a task.

    Returns checkpoints ordered by triggered_at (newest first).

    **Path parameters:**
    - task_id: UUID of the task

    **Response:**
    - checkpoints: List of checkpoint summaries
    - total: Total number of checkpoints
    """
    try:
        checkpoints = await checkpoint_service.list_task_checkpoints(task_id)

        checkpoint_responses = [
            CheckpointResponse(
                checkpoint_id=cp.checkpoint_id,
                task_id=cp.task_id,
                status=CheckpointStatus(cp.status),
                subtasks_completed=[UUID(sid) for sid in cp.subtasks_completed],
                user_decision=UserDecision(cp.user_decision) if cp.user_decision else None,
                decision_notes=cp.decision_notes,
                triggered_at=cp.triggered_at,
                reviewed_at=cp.reviewed_at
            )
            for cp in checkpoints
        ]

        return CheckpointListResponse(
            checkpoints=checkpoint_responses,
            total=len(checkpoint_responses)
        )

    except Exception as e:
        logger.error("List checkpoints failed", task_id=str(task_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list checkpoints: {str(e)}"
        )


@router.get(
    "/checkpoints/{checkpoint_id}",
    response_model=CheckpointResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Checkpoint Details",
    description="Get detailed information about a specific checkpoint"
)
async def get_checkpoint(
    checkpoint_id: UUID,
    checkpoint_service: CheckpointService = Depends(get_checkpoint_service),
    current_user: User = Depends(require_auth)
):
    """
    Get detailed checkpoint information.

    Returns:
    - Checkpoint details
    - Context information about why checkpoint was triggered
    - Agent output from completed subtasks
    - Review report (evaluation scores)

    **Path parameters:**
    - checkpoint_id: UUID of the checkpoint

    **Response:**
    - Complete checkpoint information including subtask details and evaluations
    - Returns 404 if checkpoint not found
    """
    try:
        checkpoint_data = await checkpoint_service.get_checkpoint_details(checkpoint_id)

        if not checkpoint_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint {checkpoint_id} not found"
            )

        # Build response with detailed information
        subtask_details = [
            SubtaskInfo(**subtask)
            for subtask in checkpoint_data["subtask_details"]
        ]

        evaluations = [
            EvaluationInfo(**evaluation)
            for evaluation in checkpoint_data["evaluations"]
        ]

        return CheckpointResponse(
            checkpoint_id=checkpoint_data["checkpoint_id"],
            task_id=checkpoint_data["task_id"],
            status=CheckpointStatus(checkpoint_data["status"]),
            subtasks_completed=[UUID(sid) for sid in checkpoint_data["subtasks_completed"]],
            user_decision=UserDecision(checkpoint_data["user_decision"]) if checkpoint_data["user_decision"] else None,
            decision_notes=checkpoint_data["decision_notes"],
            triggered_at=checkpoint_data["triggered_at"],
            reviewed_at=checkpoint_data["reviewed_at"],
            subtask_details=subtask_details,
            evaluations=evaluations
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get checkpoint failed", checkpoint_id=str(checkpoint_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get checkpoint: {str(e)}"
        )


@router.post(
    "/checkpoints/{checkpoint_id}/decision",
    response_model=CheckpointDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Checkpoint Decision",
    description="Submit user decision on a checkpoint (accept, correct, or reject)"
)
async def submit_checkpoint_decision(
    checkpoint_id: UUID,
    request: CheckpointDecisionRequest,
    checkpoint_service: CheckpointService = Depends(get_checkpoint_service),
    current_user: User = Depends(require_auth)
):
    """
    Submit user decision on a checkpoint.

    Handles three types of decisions:
    - **accept**: Continue to next subtask (checkpoint status → approved, task status → in_progress)
    - **correct**: Create fix subtask with user feedback (checkpoint status → corrected, creates Correction records)
    - **reject**: Mark task as cancelled (checkpoint status → rejected, task status → cancelled)

    Updates:
    - Checkpoint record with user_decision and user_feedback
    - Task status accordingly
    - Creates Correction records if decision is "correct"
    - Updates subtask status to "correcting" for corrections

    **Path parameters:**
    - checkpoint_id: UUID of the checkpoint

    **Request body:**
    - decision: "accept", "correct", or "reject"
    - feedback: User feedback or correction instructions
    - correction_type: Type of correction (e.g., "incomplete", "bug", "style")
    - reference_files: Reference files or documentation links
    - apply_to_future: Whether to apply this correction pattern to future tasks

    **Response:**
    - checkpoint_id: UUID of the checkpoint
    - status: Updated checkpoint status
    - message: Response message
    - task_status: Updated task status
    - corrections_created: Number of corrections created (if decision is "correct")
    - next_action: Description of what happens next
    """
    try:
        result = await checkpoint_service.process_decision(
            checkpoint_id=checkpoint_id,
            decision=request.decision.value,
            feedback=request.feedback,
            correction_type=request.correction_type,
            reference_files=request.reference_files,
            apply_to_future=request.apply_to_future
        )

        return CheckpointDecisionResponse(
            checkpoint_id=result["checkpoint_id"],
            status=CheckpointStatus(result["status"]),
            message="Checkpoint decision processed successfully",
            task_status=result["task_status"],
            corrections_created=result["corrections_created"],
            next_action=result["next_action"]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Submit checkpoint decision failed", checkpoint_id=str(checkpoint_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit checkpoint decision: {str(e)}"
        )


@router.get(
    "/tasks/{task_id}/checkpoints/history",
    response_model=CheckpointHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Checkpoint History",
    description="Get timeline of all checkpoints for a task"
)
async def get_checkpoint_history(
    task_id: UUID,
    checkpoint_service: CheckpointService = Depends(get_checkpoint_service),
    current_user: User = Depends(require_auth)
):
    """
    Get checkpoint history timeline for a task.

    Returns:
    - Timeline of all checkpoints
    - Includes: time, type, user_decision, feedback
    - Statistics about checkpoints (total, approved, corrected, rejected, pending)

    **Path parameters:**
    - task_id: UUID of the task

    **Response:**
    - task_id: UUID of the task
    - checkpoints: List of checkpoint history items ordered by time
    - total: Total number of checkpoints
    - statistics: Statistics about checkpoint outcomes
    """
    try:
        history_data = await checkpoint_service.get_checkpoint_history(task_id)

        # Build history items
        history_items = []
        for cp in history_data["checkpoints"]:
            # Extract trigger reason from subtasks_completed if it's stored there
            # (in the actual implementation, you might want to add a trigger_reason field to the model)
            trigger_reason = None

            history_items.append(
                CheckpointHistoryItem(
                    checkpoint_id=cp.checkpoint_id,
                    status=CheckpointStatus(cp.status),
                    subtasks_completed=[UUID(sid) for sid in cp.subtasks_completed],
                    user_decision=UserDecision(cp.user_decision) if cp.user_decision else None,
                    decision_notes=cp.decision_notes,
                    triggered_at=cp.triggered_at,
                    reviewed_at=cp.reviewed_at,
                    trigger_reason=trigger_reason
                )
            )

        return CheckpointHistoryResponse(
            task_id=history_data["task_id"],
            checkpoints=history_items,
            total=history_data["total"],
            statistics=history_data["statistics"]
        )

    except Exception as e:
        logger.error("Get checkpoint history failed", task_id=str(task_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get checkpoint history: {str(e)}"
        )


@router.get(
    "/checkpoints/{checkpoint_id}/rollback/preview",
    status_code=status.HTTP_200_OK,
    summary="Preview Rollback",
    description="Preview what will be affected by rolling back to a checkpoint"
)
async def preview_rollback(
    checkpoint_id: UUID,
    checkpoint_service: CheckpointService = Depends(get_checkpoint_service),
    current_user: User = Depends(require_auth)
):
    """
    Preview what will be affected by rolling back to a checkpoint.

    This is a read-only operation that shows:
    - Subtasks that will be reset to pending
    - Evaluations that will be cleared
    - Later checkpoints that will be deleted
    - New task progress after rollback

    **Path parameters:**
    - checkpoint_id: UUID of the target checkpoint

    **Response:**
    - checkpoint_id: Target checkpoint UUID
    - task_id: Task UUID
    - subtasks_to_reset: List of subtasks that will be reset
    - evaluations_to_clear: Number of evaluations that will be cleared
    - checkpoints_to_delete: Number of later checkpoints to delete
    - can_rollback: Whether rollback is allowed
    """
    try:
        preview = await checkpoint_service.get_rollback_preview(checkpoint_id)
        return preview

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Rollback preview failed", checkpoint_id=str(checkpoint_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview rollback: {str(e)}"
        )


@router.post(
    "/checkpoints/{checkpoint_id}/rollback",
    response_model=RollbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Rollback to Checkpoint",
    description="Rollback task state to a specific checkpoint"
)
async def rollback_to_checkpoint(
    checkpoint_id: UUID,
    request: RollbackRequest,
    checkpoint_service: CheckpointService = Depends(get_checkpoint_service),
    current_user: User = Depends(require_auth)
):
    """
    Rollback task state to a specific checkpoint.

    This operation:
    1. Resets all subtasks completed AFTER the checkpoint to 'pending'
    2. Clears output and error fields for those subtasks
    3. Optionally clears evaluations for rolled-back subtasks
    4. Deletes all checkpoints created after the target checkpoint
    5. Updates task progress accordingly
    6. Creates audit trail for the rollback

    **WARNING**: This is a destructive operation. Use preview endpoint first.

    **Path parameters:**
    - checkpoint_id: UUID of the target checkpoint to rollback to

    **Request body:**
    - reason: Optional reason for rollback (for audit trail)
    - reset_evaluations: Whether to also clear evaluations (default: True)

    **Response:**
    - checkpoint_id: Target checkpoint UUID
    - task_id: Task UUID
    - subtasks_reset: Number of subtasks reset
    - evaluations_cleared: Number of evaluations cleared
    - task_status: Updated task status
    - task_progress: Updated task progress
    """
    try:
        result = await checkpoint_service.rollback_to_checkpoint(
            checkpoint_id=checkpoint_id,
            reason=request.reason,
            reset_evaluations=request.reset_evaluations
        )

        return RollbackResponse(
            checkpoint_id=result["checkpoint_id"],
            task_id=result["task_id"],
            message=result["message"],
            subtasks_reset=result["subtasks_reset"],
            evaluations_cleared=result["evaluations_cleared"],
            task_status=result["task_status"],
            task_progress=result["task_progress"]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Rollback failed", checkpoint_id=str(checkpoint_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )
