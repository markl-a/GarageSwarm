"""
Templates API

Workflow template management endpoints for creating and managing reusable task templates.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.dependencies import get_db
from src.services.template_service import TemplateService
from src.exceptions import NotFoundError, ValidationError
from src.auth.dependencies import require_auth
from src.models.user import User
from src.schemas.template import (
    TemplateCreateRequest,
    TemplateCreateResponse,
    TemplateDetailResponse,
    TemplateListResponse,
    TemplateSummary,
    TemplateUpdateRequest,
    TemplateApplyRequest,
    TemplateApplyResponse,
    TemplateCategory,
    TemplateStepResponse,
)
from src.schemas.subtask import SubtaskResponse, SubtaskStatus

router = APIRouter()
logger = structlog.get_logger()


async def get_template_service(db: AsyncSession = Depends(get_db)) -> TemplateService:
    """Dependency to get TemplateService instance"""
    return TemplateService(db)


@router.post(
    "/templates",
    response_model=TemplateCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Template",
    description="Create a new workflow template",
)
async def create_template(
    request: TemplateCreateRequest,
    template_service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(require_auth),
):
    """
    Create a new workflow template.

    **Required fields:**
    - name: Template name (unique)
    - description: Template description
    - category: Template category
    - steps: List of template steps (at least one required)

    **Optional fields:**
    - is_active: Whether template is active (default: true)
    - default_checkpoint_frequency: Default checkpoint frequency
    - default_privacy_level: Default privacy level
    - default_tool_preferences: Default AI tools
    - tags: Template tags
    - estimated_duration: Estimated completion time in minutes
    - complexity_level: Overall complexity (1-5)
    - template_metadata: Additional metadata

    **Response:**
    - template_id: UUID of the created template
    - name: Template name
    - message: Confirmation message
    """
    try:
        # Convert steps to dict format
        steps_data = [step.model_dump() for step in request.steps]

        template = await template_service.create_template(
            name=request.name,
            description=request.description,
            category=request.category.value,
            steps=steps_data,
            is_active=request.is_active,
            default_checkpoint_frequency=request.default_checkpoint_frequency,
            default_privacy_level=request.default_privacy_level,
            default_tool_preferences=request.default_tool_preferences,
            tags=request.tags,
            estimated_duration=request.estimated_duration,
            complexity_level=request.complexity_level,
            template_metadata=request.template_metadata,
        )

        return TemplateCreateResponse(
            template_id=template.template_id,
            name=template.name,
            message="Template created successfully",
        )

    except ValueError as e:
        raise ValidationError(str(e))


@router.get(
    "/templates",
    response_model=TemplateListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Templates",
    description="Get list of all workflow templates with optional filtering and pagination",
)
async def list_templates(
    category: Optional[TemplateCategory] = Query(
        None, description="Filter by category"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    tags: Optional[str] = Query(
        None, description="Filter by tags (comma-separated)"
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    template_service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(require_auth),
):
    """
    List all workflow templates with optional filtering.

    **Query parameters:**
    - category: Filter by category (development, testing, documentation, devops, review)
    - is_active: Filter by active status (true/false)
    - tags: Filter by tags (comma-separated, e.g., "api,backend")
    - limit: Maximum number of results (1-100, default 50)
    - offset: Offset for pagination (default 0)

    **Response:**
    - templates: List of template summaries
    - total: Total number of templates matching the filter
    - limit: Applied limit
    - offset: Applied offset
    """
    # Parse tags
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    category_str = category.value if category else None
    templates, total = await template_service.list_templates(
        category=category_str,
        is_active=is_active,
        tags=tag_list,
        limit=limit,
        offset=offset,
    )

    template_summaries = [
        TemplateSummary(
            template_id=template.template_id,
            name=template.name,
            description=(
                template.description[:200]
                if len(template.description) > 200
                else template.description
            ),
            category=TemplateCategory(template.category),
            is_active=template.is_active,
            is_system=template.is_system,
            tags=template.tags,
            estimated_duration=template.estimated_duration,
            complexity_level=template.complexity_level,
            usage_count=template.usage_count,
            step_count=len(template.steps) if template.steps else 0,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
        for template in templates
    ]

    return TemplateListResponse(
        templates=template_summaries, total=total, limit=limit, offset=offset
    )


@router.get(
    "/templates/popular",
    response_model=TemplateListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Popular Templates",
    description="Get most popular templates by usage count",
)
async def get_popular_templates(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    template_service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(require_auth),
):
    """
    Get most popular templates by usage count.

    **Query parameters:**
    - limit: Maximum number of results (1-50, default 10)

    **Response:**
    - templates: List of popular templates
    - total: Total number of templates returned
    """
    templates = await template_service.get_popular_templates(limit=limit)

    template_summaries = [
        TemplateSummary(
            template_id=template.template_id,
            name=template.name,
            description=(
                template.description[:200]
                if len(template.description) > 200
                else template.description
            ),
            category=TemplateCategory(template.category),
            is_active=template.is_active,
            is_system=template.is_system,
            tags=template.tags,
            estimated_duration=template.estimated_duration,
            complexity_level=template.complexity_level,
            usage_count=template.usage_count,
            step_count=len(template.steps) if template.steps else 0,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
        for template in templates
    ]

    return TemplateListResponse(
        templates=template_summaries,
        total=len(template_summaries),
        limit=limit,
        offset=0,
    )


@router.get(
    "/templates/{template_id}",
    response_model=TemplateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Template Details",
    description="Get detailed information about a specific workflow template",
)
async def get_template(
    template_id: UUID,
    template_service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(require_auth),
):
    """
    Get detailed information about a specific workflow template.

    **Path parameters:**
    - template_id: UUID of the template

    **Response:**
    - Complete template information including all steps
    - Returns 404 if template not found
    """
    template = await template_service.get_template(template_id)

    if not template:
        raise NotFoundError("Template", str(template_id))

    # Build step responses
    step_responses = [
        TemplateStepResponse(
            step_id=step.step_id,
            template_id=step.template_id,
            name=step.name,
            description=step.description,
            step_order=step.step_order,
            step_type=step.step_type,
            depends_on=step.depends_on,
            recommended_tool=step.recommended_tool,
            complexity=step.complexity,
            priority=step.priority,
            is_required=step.is_required,
            is_parallel=step.is_parallel,
            step_metadata=step.step_metadata,
            created_at=step.created_at,
            updated_at=step.updated_at,
        )
        for step in (template.steps or [])
    ]

    return TemplateDetailResponse(
        template_id=template.template_id,
        name=template.name,
        description=template.description,
        category=TemplateCategory(template.category),
        is_active=template.is_active,
        is_system=template.is_system,
        default_checkpoint_frequency=template.default_checkpoint_frequency,
        default_privacy_level=template.default_privacy_level,
        default_tool_preferences=template.default_tool_preferences,
        tags=template.tags,
        estimated_duration=template.estimated_duration,
        complexity_level=template.complexity_level,
        template_metadata=template.template_metadata,
        usage_count=template.usage_count,
        created_by=template.created_by,
        steps=step_responses,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.patch(
    "/templates/{template_id}",
    response_model=TemplateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Template",
    description="Update an existing workflow template",
)
async def update_template(
    template_id: UUID,
    request: TemplateUpdateRequest,
    template_service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(require_auth),
):
    """
    Update an existing workflow template.

    **Path parameters:**
    - template_id: UUID of the template to update

    **Note:** System templates cannot be modified.

    **Response:**
    - Updated template details
    """
    try:
        template = await template_service.update_template(
            template_id=template_id,
            name=request.name,
            description=request.description,
            category=request.category.value if request.category else None,
            is_active=request.is_active,
            default_checkpoint_frequency=request.default_checkpoint_frequency,
            default_privacy_level=request.default_privacy_level,
            default_tool_preferences=request.default_tool_preferences,
            tags=request.tags,
            estimated_duration=request.estimated_duration,
            complexity_level=request.complexity_level,
            template_metadata=request.template_metadata,
        )

        # Reload with steps
        template = await template_service.get_template(template_id)

        step_responses = [
            TemplateStepResponse(
                step_id=step.step_id,
                template_id=step.template_id,
                name=step.name,
                description=step.description,
                step_order=step.step_order,
                step_type=step.step_type,
                depends_on=step.depends_on,
                recommended_tool=step.recommended_tool,
                complexity=step.complexity,
                priority=step.priority,
                is_required=step.is_required,
                is_parallel=step.is_parallel,
                step_metadata=step.step_metadata,
                created_at=step.created_at,
                updated_at=step.updated_at,
            )
            for step in (template.steps or [])
        ]

        return TemplateDetailResponse(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            category=TemplateCategory(template.category),
            is_active=template.is_active,
            is_system=template.is_system,
            default_checkpoint_frequency=template.default_checkpoint_frequency,
            default_privacy_level=template.default_privacy_level,
            default_tool_preferences=template.default_tool_preferences,
            tags=template.tags,
            estimated_duration=template.estimated_duration,
            complexity_level=template.complexity_level,
            template_metadata=template.template_metadata,
            usage_count=template.usage_count,
            created_by=template.created_by,
            steps=step_responses,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )

    except ValueError as e:
        raise ValidationError(str(e))


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Template",
    description="Delete a workflow template",
)
async def delete_template(
    template_id: UUID,
    template_service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(require_auth),
):
    """
    Delete a workflow template.

    **Path parameters:**
    - template_id: UUID of the template to delete

    **Note:** System templates cannot be deleted.

    **Response:**
    - 204 No Content on success
    """
    try:
        await template_service.delete_template(template_id)
    except ValueError as e:
        raise ValidationError(str(e))


@router.post(
    "/tasks/{task_id}/apply-template",
    response_model=TemplateApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply Template to Task",
    description="Apply a workflow template to a task by creating subtasks from template steps",
)
async def apply_template_to_task(
    task_id: UUID,
    request: TemplateApplyRequest,
    template_service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(require_auth),
):
    """
    Apply a workflow template to a task.

    This creates subtasks based on the template's steps, mapping:
    - Step name → Subtask name
    - Step description → Subtask description
    - Step type → Subtask type
    - Step dependencies → Subtask dependencies
    - Step recommended_tool → Subtask recommended_tool
    - Step complexity → Subtask complexity
    - Step priority → Subtask priority

    **Path parameters:**
    - task_id: UUID of the task

    **Request body:**
    - template_id: UUID of the template to apply

    **Response:**
    - task_id: UUID of the task
    - template_id: UUID of the applied template
    - template_name: Name of the applied template
    - subtask_count: Number of subtasks created
    - message: Confirmation message
    """
    try:
        subtasks = await template_service.apply_template_to_task(
            template_id=request.template_id, task_id=task_id
        )

        # Get template name
        template = await template_service.get_template(request.template_id)

        return TemplateApplyResponse(
            task_id=task_id,
            template_id=request.template_id,
            template_name=template.name if template else "Unknown",
            subtask_count=len(subtasks),
            message=f"Template applied successfully, created {len(subtasks)} subtasks",
        )

    except ValueError as e:
        raise ValidationError(str(e))
