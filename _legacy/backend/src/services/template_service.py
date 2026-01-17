"""Template Service - Business logic for workflow template management"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload
import structlog

from src.models.template import WorkflowTemplate, TemplateStep
from src.models.task import Task
from src.models.subtask import Subtask

logger = structlog.get_logger()


class TemplateService:
    """Service for managing workflow template operations"""

    def __init__(self, db: AsyncSession):
        """Initialize TemplateService

        Args:
            db: Database session
        """
        self.db = db

    async def create_template(
        self,
        name: str,
        description: str,
        category: str,
        steps: List[Dict[str, Any]],
        is_active: bool = True,
        is_system: bool = False,
        default_checkpoint_frequency: str = "medium",
        default_privacy_level: str = "normal",
        default_tool_preferences: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        estimated_duration: Optional[int] = None,
        complexity_level: Optional[int] = None,
        template_metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
    ) -> WorkflowTemplate:
        """Create a new workflow template

        Args:
            name: Template name (unique)
            description: Template description
            category: Template category
            steps: List of step definitions
            is_active: Whether template is active
            is_system: Whether template is a system template
            default_checkpoint_frequency: Default checkpoint frequency
            default_privacy_level: Default privacy level
            default_tool_preferences: Default AI tools
            tags: Template tags
            estimated_duration: Estimated completion time in minutes
            complexity_level: Complexity rating (1-5)
            template_metadata: Additional metadata
            created_by: Creator user ID

        Returns:
            WorkflowTemplate: Created template instance

        Raises:
            ValueError: If template with same name exists or validation fails
        """
        logger.info(
            "Creating workflow template",
            name=name,
            category=category,
            step_count=len(steps),
        )

        try:
            # Check if template with same name exists
            result = await self.db.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.name == name)
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise ValueError(f"Template with name '{name}' already exists")

            # Create template
            template = WorkflowTemplate(
                name=name,
                description=description,
                category=category,
                is_active=is_active,
                is_system=is_system,
                default_checkpoint_frequency=default_checkpoint_frequency,
                default_privacy_level=default_privacy_level,
                default_tool_preferences=default_tool_preferences,
                tags=tags,
                estimated_duration=estimated_duration,
                complexity_level=complexity_level,
                template_metadata=template_metadata,
                created_by=created_by,
            )

            self.db.add(template)
            await self.db.flush()  # Get template_id for steps

            # Create steps
            for step_data in steps:
                step = TemplateStep(
                    template_id=template.template_id,
                    name=step_data["name"],
                    description=step_data["description"],
                    step_order=step_data["step_order"],
                    step_type=step_data["step_type"],
                    depends_on=step_data.get("depends_on"),
                    recommended_tool=step_data.get("recommended_tool"),
                    complexity=step_data.get("complexity"),
                    priority=step_data.get("priority", 0),
                    is_required=step_data.get("is_required", True),
                    is_parallel=step_data.get("is_parallel", False),
                    step_metadata=step_data.get("step_metadata"),
                )
                self.db.add(step)

            await self.db.commit()
            await self.db.refresh(template)

            logger.info(
                "Template created successfully",
                template_id=str(template.template_id),
                name=name,
            )

            return template

        except Exception as e:
            await self.db.rollback()
            logger.error("Template creation failed", error=str(e))
            raise

    async def get_template(self, template_id: UUID) -> Optional[WorkflowTemplate]:
        """Get template by ID with all steps

        Args:
            template_id: Template UUID

        Returns:
            Optional[WorkflowTemplate]: Template instance or None
        """
        result = await self.db.execute(
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .where(WorkflowTemplate.template_id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_template_by_name(self, name: str) -> Optional[WorkflowTemplate]:
        """Get template by name with all steps

        Args:
            name: Template name

        Returns:
            Optional[WorkflowTemplate]: Template instance or None
        """
        result = await self.db.execute(
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .where(WorkflowTemplate.name == name)
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[WorkflowTemplate], int]:
        """List templates with optional filtering

        Args:
            category: Filter by category
            is_active: Filter by active status
            tags: Filter by tags (any match)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            tuple: (list of templates, total count)
        """
        # Build query
        query = select(WorkflowTemplate).options(selectinload(WorkflowTemplate.steps))

        if category:
            query = query.where(WorkflowTemplate.category == category)

        if is_active is not None:
            query = query.where(WorkflowTemplate.is_active == is_active)

        if tags:
            # Filter templates that have any of the specified tags
            for tag in tags:
                query = query.where(WorkflowTemplate.tags.contains([tag]))

        # Order by usage_count descending (most popular first), then name
        query = query.order_by(
            WorkflowTemplate.usage_count.desc(), WorkflowTemplate.name
        )

        # Get total count
        count_query = select(func.count()).select_from(WorkflowTemplate)
        if category:
            count_query = count_query.where(WorkflowTemplate.category == category)
        if is_active is not None:
            count_query = count_query.where(WorkflowTemplate.is_active == is_active)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated results
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        templates = result.scalars().unique().all()

        return list(templates), total

    async def update_template(
        self,
        template_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        default_checkpoint_frequency: Optional[str] = None,
        default_privacy_level: Optional[str] = None,
        default_tool_preferences: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        estimated_duration: Optional[int] = None,
        complexity_level: Optional[int] = None,
        template_metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowTemplate:
        """Update template

        Args:
            template_id: Template UUID
            (other args): Fields to update

        Returns:
            WorkflowTemplate: Updated template

        Raises:
            ValueError: If template not found or validation fails
        """
        logger.info("Updating template", template_id=str(template_id))

        result = await self.db.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.template_id == template_id
            )
        )
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Check if template is system template
        if template.is_system:
            raise ValueError("Cannot modify system templates")

        # Update fields
        if name is not None:
            # Check if new name conflicts
            if name != template.name:
                result = await self.db.execute(
                    select(WorkflowTemplate).where(WorkflowTemplate.name == name)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    raise ValueError(f"Template with name '{name}' already exists")
            template.name = name

        if description is not None:
            template.description = description
        if category is not None:
            template.category = category
        if is_active is not None:
            template.is_active = is_active
        if default_checkpoint_frequency is not None:
            template.default_checkpoint_frequency = default_checkpoint_frequency
        if default_privacy_level is not None:
            template.default_privacy_level = default_privacy_level
        if default_tool_preferences is not None:
            template.default_tool_preferences = default_tool_preferences
        if tags is not None:
            template.tags = tags
        if estimated_duration is not None:
            template.estimated_duration = estimated_duration
        if complexity_level is not None:
            template.complexity_level = complexity_level
        if template_metadata is not None:
            template.template_metadata = template_metadata

        await self.db.commit()
        await self.db.refresh(template)

        logger.info("Template updated", template_id=str(template_id))
        return template

    async def delete_template(self, template_id: UUID) -> bool:
        """Delete template

        Args:
            template_id: Template UUID

        Returns:
            bool: True if deleted successfully

        Raises:
            ValueError: If template not found or is system template
        """
        logger.info("Deleting template", template_id=str(template_id))

        result = await self.db.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.template_id == template_id
            )
        )
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        if template.is_system:
            raise ValueError("Cannot delete system templates")

        await self.db.delete(template)
        await self.db.commit()

        logger.info("Template deleted", template_id=str(template_id))
        return True

    async def apply_template_to_task(
        self, template_id: UUID, task_id: UUID
    ) -> List[Subtask]:
        """Apply template to a task by creating subtasks from template steps

        Args:
            template_id: Template UUID
            task_id: Task UUID

        Returns:
            List[Subtask]: Created subtasks

        Raises:
            ValueError: If template or task not found
        """
        logger.info(
            "Applying template to task",
            template_id=str(template_id),
            task_id=str(task_id),
        )

        # Get template with steps
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        if not template.is_active:
            raise ValueError(f"Template {template_id} is not active")

        # Get task
        result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Create subtasks from template steps
        subtasks = []
        step_id_map = {}  # Maps step_order to subtask_id for dependencies

        for step in template.steps:
            # Map dependencies from step_order to subtask_ids
            dependencies = []
            if step.depends_on:
                for dep in step.depends_on:
                    # If dependency is an integer, treat it as step_order
                    if isinstance(dep, int) and dep in step_id_map:
                        dependencies.append(str(step_id_map[dep]))

            subtask = Subtask(
                task_id=task_id,
                name=step.name,
                description=step.description,
                status="pending",
                progress=0,
                subtask_type=step.step_type,
                recommended_tool=step.recommended_tool,
                complexity=step.complexity,
                priority=step.priority,
                dependencies=dependencies if dependencies else None,
            )

            self.db.add(subtask)
            await self.db.flush()  # Get subtask_id

            subtasks.append(subtask)
            step_id_map[step.step_order] = subtask.subtask_id

        # Update template usage count
        template.usage_count += 1

        # Update task metadata to reference template
        if task.task_metadata is None:
            task.task_metadata = {}
        task.task_metadata["template_id"] = str(template_id)
        task.task_metadata["template_name"] = template.name

        await self.db.commit()

        logger.info(
            "Template applied successfully",
            template_id=str(template_id),
            task_id=str(task_id),
            subtask_count=len(subtasks),
        )

        return subtasks

    async def get_popular_templates(self, limit: int = 10) -> List[WorkflowTemplate]:
        """Get most popular templates by usage count

        Args:
            limit: Maximum number of results

        Returns:
            List[WorkflowTemplate]: Popular templates
        """
        result = await self.db.execute(
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .where(WorkflowTemplate.is_active == True)
            .order_by(WorkflowTemplate.usage_count.desc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())
