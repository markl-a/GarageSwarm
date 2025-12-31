"""
Dependency Injection

FastAPI dependency injection functions for database, Redis, and authentication.
"""

from typing import AsyncGenerator, Optional
from uuid import UUID

import redis.asyncio as redis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings, Settings
from src.database import get_db as get_db_session
from src.logging_config import get_logger
from src.redis_client import get_redis
from src.services.redis_service import RedisService

logger = get_logger(__name__)

# Security scheme for JWT authentication
security = HTTPBearer(auto_error=False)


# ==================== Database ====================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency

    Usage:
        @router.get("/tasks")
        async def get_tasks(db: AsyncSession = Depends(get_db)):
            ...
    """
    async for session in get_db_session():
        yield session


# ==================== Redis ====================


async def get_redis_client() -> redis.Redis:
    """
    Get Redis client dependency

    Usage:
        @router.get("/cache")
        async def get_cache(redis: redis.Redis = Depends(get_redis_client)):
            ...
    """
    return get_redis()


async def get_redis_service(
    redis_client: redis.Redis = Depends(get_redis_client),
) -> RedisService:
    """
    Get Redis service dependency

    Usage:
        @router.get("/workers")
        async def get_workers(redis_service: RedisService = Depends(get_redis_service)):
            online_workers = await redis_service.get_online_workers()
            ...
    """
    return RedisService(redis_client)


# ==================== Settings ====================


def get_app_settings() -> Settings:
    """
    Get application settings dependency

    Usage:
        @router.get("/config")
        async def get_config(settings: Settings = Depends(get_app_settings)):
            return {"debug": settings.DEBUG}
    """
    return get_settings()


# ==================== Authentication ====================
# Full JWT authentication is implemented in src/auth/dependencies.py
# Re-export for convenience and backward compatibility

from src.auth.dependencies import (
    get_current_user as get_authenticated_user,
    get_current_active_user,
    require_auth,
    optional_auth,
)


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[UUID]:
    """
    Get current authenticated user ID (UUID only)

    For full User object, use src.auth.dependencies.get_current_user

    Returns:
        User UUID if authenticated, None otherwise
    """
    user = await get_authenticated_user(credentials, db)
    return user.user_id if user else None


async def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """
    Require authenticated user and return UUID

    Usage:
        @router.post("/tasks")
        async def create_task(
            user_id: UUID = Depends(require_authenticated_user)
        ):
            ...
    """
    user = await require_auth(
        await get_current_active_user(
            await get_authenticated_user(credentials, db)
        )
    )
    return user.user_id


# ==================== Rate Limiting ====================


async def check_rate_limit(
    user_id: Optional[UUID] = Depends(get_current_user_id),
    redis_service: RedisService = Depends(get_redis_service),
    settings: Settings = Depends(get_app_settings),
) -> None:
    """
    Check API rate limit for user

    Rate limit is applied per-user with configurable limits from settings.
    Anonymous users are not rate limited.

    Usage:
        @router.post("/tasks", dependencies=[Depends(check_rate_limit)])
        async def create_task(...):
            ...
    """
    if user_id is None:
        # Skip rate limiting for anonymous users
        return

    # Use generic endpoint for rate limiting (per-user global limit)
    endpoint = "api_request"

    # Get rate limit settings (default: 100 requests per 60 seconds)
    limit = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
    window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)

    within_limit = await redis_service.check_rate_limit(
        user_id, endpoint, limit=limit, window=window
    )

    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )
