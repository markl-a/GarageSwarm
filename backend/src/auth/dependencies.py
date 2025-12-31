"""
Authentication Dependencies

FastAPI dependencies for JWT authentication and authorization.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt_handler import verify_token_async, TokenType
from src.database import get_db
from src.models.user import User
from src.logging_config import get_logger

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session

    Returns:
        User object if authenticated, None otherwise

    Raises:
        HTTPException: If token is invalid or user not found

    Example:
        @app.get("/profile")
        async def get_profile(user: User = Depends(get_current_user)):
            return {"username": user.username}
    """
    if not credentials:
        return None

    token = credentials.credentials

    try:
        # Verify and decode token (async version checks Redis blacklist)
        payload = await verify_token_async(token, expected_type=TokenType.ACCESS)

        # Extract user ID from token
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            logger.warning("Token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = UUID(user_id_str)

    except (JWTError, ValueError) as e:
        logger.warning("Token verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("User not found", user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("User authenticated successfully", user_id=str(user_id), username=user.username)
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Get current authenticated and active user

    Args:
        user: Current user from get_current_user dependency

    Returns:
        User object if active

    Raises:
        HTTPException: If user is inactive

    Example:
        @app.get("/dashboard")
        async def get_dashboard(user: User = Depends(get_current_active_user)):
            return {"message": f"Welcome {user.username}"}
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user has is_active field (optional field)
    if hasattr(user, "is_active") and not user.is_active:
        logger.warning("Inactive user attempted access", user_id=str(user.user_id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def require_auth(
    user: User = Depends(get_current_active_user),
) -> User:
    """
    Require authentication for endpoint

    Alias for get_current_active_user for better semantic clarity.

    Args:
        user: Current active user

    Returns:
        User object

    Example:
        @app.post("/tasks")
        async def create_task(
            task_data: TaskCreate,
            user: User = Depends(require_auth)
        ):
            return await task_service.create(task_data, user.user_id)
    """
    return user


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Optional authentication - returns user if authenticated, None otherwise

    Does not raise exceptions for missing/invalid tokens.

    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session

    Returns:
        User object if authenticated, None otherwise

    Example:
        @app.get("/public-data")
        async def get_data(user: Optional[User] = Depends(optional_auth)):
            if user:
                return {"data": "premium", "user": user.username}
            return {"data": "basic"}
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        # Silently fail for optional auth
        return None
