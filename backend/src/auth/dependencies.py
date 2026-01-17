"""
Authentication Dependencies

FastAPI dependencies for protecting routes.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models.user import User
from src.logging_config import get_logger
from .jwt_handler import verify_token_async, TokenType

logger = get_logger(__name__)

# Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = await verify_token_async(token, TokenType.ACCESS)
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except Exception as e:
        logger.warning("Token validation failed", error=str(e))
        raise credentials_exception

    # Fetch user from database
    result = await db.execute(
        select(User).where(User.user_id == UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("User not found", user_id=user_id)
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active user object

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.

    Useful for endpoints that work for both authenticated and anonymous users.
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = await verify_token_async(token, TokenType.ACCESS)
        user_id = payload.get("sub")

        if user_id is None:
            return None

        result = await db.execute(
            select(User).where(User.user_id == UUID(user_id))
        )
        return result.scalar_one_or_none()

    except Exception:
        return None
