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


# ==================== Authentication (Placeholder) ====================


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[UUID]:
    """
    Get current authenticated user (JWT validation)

    This is a placeholder for future authentication implementation.
    Currently returns None (no authentication required).

    Args:
        credentials: JWT token from Authorization header
        db: Database session

    Returns:
        User UUID if authenticated, None otherwise

    Raises:
        HTTPException: If token is invalid
    """
    # TODO: Implement JWT validation in Sprint 2+
    # For now, return None (no authentication)

    if credentials is None:
        # No token provided - allow anonymous access for now
        return None

    # Placeholder JWT validation
    # token = credentials.credentials
    # try:
    #     payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    #     user_id = payload.get("sub")
    #     if user_id is None:
    #         raise HTTPException(status_code=401, detail="Invalid token")
    #     return UUID(user_id)
    # except jwt.JWTError:
    #     raise HTTPException(status_code=401, detail="Invalid token")

    return None


async def require_authenticated_user(
    current_user: Optional[UUID] = Depends(get_current_user),
) -> UUID:
    """
    Require authenticated user (raises 401 if not authenticated)

    Usage:
        @router.post("/tasks")
        async def create_task(
            user_id: UUID = Depends(require_authenticated_user)
        ):
            ...
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


# ==================== Rate Limiting ====================


async def check_rate_limit(
    user_id: Optional[UUID] = Depends(get_current_user),
    redis_service: RedisService = Depends(get_redis_service),
    settings: Settings = Depends(get_app_settings),
) -> None:
    """
    Check API rate limit for user

    Usage:
        @router.post("/tasks", dependencies=[Depends(check_rate_limit)])
        async def create_task(...):
            ...
    """
    if user_id is None:
        # Skip rate limiting for anonymous users (for now)
        return

    # TODO: Get endpoint from request context
    endpoint = "/api/v1/tasks"

    within_limit = await redis_service.check_rate_limit(
        user_id, endpoint, limit=100, window=60
    )

    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )
