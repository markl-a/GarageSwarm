"""
Tasks API (Placeholder)

Task management endpoints.
Will be implemented in Sprint 2.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/tasks")
async def create_task():
    """
    Create a new task

    TODO: Implement in Sprint 2
    """
    return {"message": "Task creation endpoint - Coming in Sprint 2"}


@router.get("/tasks")
async def list_tasks():
    """
    List all tasks

    TODO: Implement in Sprint 2
    """
    return {"message": "Task list endpoint - Coming in Sprint 2"}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """
    Get task details by ID

    TODO: Implement in Sprint 2
    """
    return {"message": f"Task {task_id} details - Coming in Sprint 2"}
