"""
API v1 Package

Contains all v1 API route modules.
"""

from fastapi import APIRouter

from . import auth, tasks, workers, workflows, health

router = APIRouter()

# Include all route modules
router.include_router(health.router, tags=["Health"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
router.include_router(workers.router, prefix="/workers", tags=["Workers"])
router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
