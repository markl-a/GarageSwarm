"""
Workflow Endpoints

Workflow CRUD and execution management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.database import get_db
from src.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowStatus, NodeStatus
from src.models.user import User
from src.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowNodeResponse,
    WorkflowEdgeResponse,
)
from src.auth.dependencies import get_current_active_user
from src.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List workflows for the current user.
    """
    query = select(Workflow).where(Workflow.user_id == current_user.user_id)

    if status:
        query = query.where(Workflow.status == status)

    query = query.order_by(Workflow.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    workflows = result.scalars().all()

    # Get total count
    count_query = select(func.count()).select_from(Workflow).where(
        Workflow.user_id == current_user.user_id
    )
    if status:
        count_query = count_query.where(Workflow.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return WorkflowListResponse(
        workflows=[
            WorkflowResponse(
                **w.__dict__,
                progress=w.progress,
            )
            for w in workflows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new workflow.
    """
    workflow = Workflow(
        user_id=current_user.user_id,
        name=data.name,
        description=data.description,
        workflow_type=data.workflow_type,
        context=data.context,
        status=WorkflowStatus.DRAFT.value,
    )

    db.add(workflow)
    await db.flush()

    # Create nodes if provided
    if data.nodes:
        for node_data in data.nodes:
            node = WorkflowNode(
                workflow_id=workflow.workflow_id,
                name=node_data.name,
                node_type=node_data.node_type,
                order_index=node_data.order_index,
                agent_config=node_data.agent_config,
                condition_config=node_data.condition_config,
                dependencies=node_data.dependencies,
                max_retries=node_data.max_retries,
                status=NodeStatus.PENDING.value,
            )
            db.add(node)

        workflow.total_nodes = len(data.nodes)

    # Create edges if provided
    if data.edges:
        for edge_data in data.edges:
            edge = WorkflowEdge(
                workflow_id=workflow.workflow_id,
                from_node_id=edge_data.from_node_id,
                to_node_id=edge_data.to_node_id,
                condition=edge_data.condition,
                label=edge_data.label,
            )
            db.add(edge)

    await db.commit()
    await db.refresh(workflow)

    logger.info(
        "Workflow created",
        workflow_id=str(workflow.workflow_id),
        user_id=str(current_user.user_id),
    )

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.get("/test/{workflow_id}")
async def get_workflow_test(workflow_id: str):
    """Simple test endpoint."""
    return {"test": "ok", "workflow_id": workflow_id}


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific workflow with nodes and edges.
    """
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Build response dict directly
    response = {
        "workflow_id": str(workflow.workflow_id),
        "user_id": str(workflow.user_id),
        "name": workflow.name,
        "description": workflow.description,
        "workflow_type": workflow.workflow_type,
        "status": workflow.status,
        "dag_definition": workflow.dag_definition,
        "context": workflow.context,
        "result": workflow.result,
        "error": workflow.error,
        "total_nodes": workflow.total_nodes or 0,
        "completed_nodes": workflow.completed_nodes or 0,
        "progress": workflow.progress,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
        "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
        "nodes": [],
        "edges": [],
    }

    # Add nodes
    for n in workflow.nodes:
        response["nodes"].append({
            "node_id": str(n.node_id),
            "workflow_id": str(n.workflow_id),
            "name": n.name,
            "node_type": n.node_type,
            "status": n.status,
            "order_index": n.order_index or 0,
            "retry_count": n.retry_count or 0,
            "max_retries": n.max_retries or 3,
        })

    # Add edges
    for e in workflow.edges:
        response["edges"].append({
            "edge_id": str(e.edge_id),
            "from_node_id": str(e.from_node_id),
            "to_node_id": str(e.to_node_id),
        })

    return response


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Only allow updates if workflow is in draft or failed state
    if workflow.status not in (WorkflowStatus.DRAFT.value, WorkflowStatus.FAILED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update workflow with status: {workflow.status}",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workflow, field, value)

    await db.commit()
    await db.refresh(workflow)

    logger.info("Workflow updated", workflow_id=str(workflow_id))

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Don't allow deletion of running workflows
    if workflow.status == WorkflowStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running workflow",
        )

    await db.delete(workflow)
    await db.commit()

    logger.info("Workflow deleted", workflow_id=str(workflow_id))

    return None


@router.post("/{workflow_id}/execute", response_model=WorkflowResponse)
async def execute_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start workflow execution.
    """
    from src.services.workflow_engine import get_workflow_engine

    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes))
        .where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if workflow.status not in (WorkflowStatus.DRAFT.value, WorkflowStatus.FAILED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot execute workflow with status: {workflow.status}",
        )

    if not workflow.nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow has no nodes",
        )

    # Reset node statuses
    for node in workflow.nodes:
        node.status = NodeStatus.PENDING.value
        node.started_at = None
        node.completed_at = None
        node.output = None
        node.error = None
        node.retry_count = 0

    workflow.completed_nodes = 0
    workflow.error = None
    workflow.result = None

    await db.commit()

    # Start workflow execution via engine
    engine = get_workflow_engine(db)
    try:
        workflow = await engine.start_workflow(workflow_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await db.refresh(workflow)

    logger.info("Workflow execution started", workflow_id=str(workflow_id))

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.post("/{workflow_id}/pause", response_model=WorkflowResponse)
async def pause_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pause a running workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if workflow.status != WorkflowStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only running workflows can be paused",
        )

    workflow.status = WorkflowStatus.PAUSED.value
    await db.commit()
    await db.refresh(workflow)

    logger.info("Workflow paused", workflow_id=str(workflow_id))

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.post("/{workflow_id}/resume", response_model=WorkflowResponse)
async def resume_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resume a paused workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if workflow.status != WorkflowStatus.PAUSED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paused workflows can be resumed",
        )

    workflow.status = WorkflowStatus.RUNNING.value
    await db.commit()
    await db.refresh(workflow)

    logger.info("Workflow resumed", workflow_id=str(workflow_id))

    # TODO: Trigger async workflow execution via background task or message queue

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.post("/{workflow_id}/cancel", response_model=WorkflowResponse)
async def cancel_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if workflow.status in (WorkflowStatus.COMPLETED.value, WorkflowStatus.CANCELLED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel workflow with status: {workflow.status}",
        )

    workflow.status = WorkflowStatus.CANCELLED.value
    workflow.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(workflow)

    logger.info("Workflow cancelled", workflow_id=str(workflow_id))

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )
