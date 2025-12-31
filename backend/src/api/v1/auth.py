"""
Authentication API Endpoints

REST API for user authentication (login, register, refresh, logout).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_active_user, optional_auth
from src.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token_async,
    blacklist_token_async,
    TokenType,
)
from src.auth.password import hash_password, verify_password
from src.database import get_db
from src.dependencies import get_redis_service
from src.logging_config import get_logger
from src.models.user import User
from src.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    UserResponse,
    RegisterResponse,
    LoginResponse,
    LogoutResponse,
    PasswordChangeRequest,
    PasswordChangeResponse,
)
from src.services.redis_service import RedisService

logger = get_logger(__name__)

router = APIRouter()


# Rate limiting configuration
REGISTER_RATE_LIMIT = 5  # 5 registrations per window
REGISTER_RATE_WINDOW = 3600  # 1 hour window
LOGIN_RATE_LIMIT = 10  # 10 login attempts per window
LOGIN_RATE_WINDOW = 300  # 5 minute window


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxy headers"""
    # Check X-Forwarded-For header first (for reverse proxy scenarios)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client host
    return request.client.host if request.client else "unknown"


@router.post(
    "/auth/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with username, email, and password",
)
async def register(
    request: UserRegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service),
):
    """
    Register a new user account

    Creates a new user with hashed password and returns user details.

    - **username**: 3-50 characters, alphanumeric with hyphens/underscores
    - **email**: Valid email address
    - **password**: Minimum 8 characters

    Rate limit: 5 registrations per hour per IP address
    """
    # Rate limiting check
    client_ip = get_client_ip(http_request)
    allowed, remaining, retry_after = await redis_service.check_ip_rate_limit(
        ip_address=client_ip,
        endpoint="auth:register",
        limit=REGISTER_RATE_LIMIT,
        window=REGISTER_RATE_WINDOW
    )

    if not allowed:
        logger.warning(
            "Registration rate limit exceeded",
            ip=client_ip,
            retry_after=retry_after
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)}
        )

    # Check if username already exists
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        logger.warning("Registration failed: username exists", username=request.username)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        logger.warning("Registration failed: email exists", email=request.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user with hashed password
    user = User(
        username=request.username,
        email=request.email,
        password_hash=hash_password(request.password),
    )

    # Add is_active if field exists
    if hasattr(User, "is_active"):
        user.is_active = True

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        "User registered successfully",
        user_id=str(user.user_id),
        username=user.username,
    )

    # Build user response
    user_data = UserResponse.model_validate(user)

    # Add is_active to response if it exists
    if hasattr(user, "is_active"):
        user_data.is_active = user.is_active
    else:
        user_data.is_active = True

    return RegisterResponse(user=user_data)


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user and return access + refresh tokens",
)
async def login(
    request: UserLoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service),
):
    """
    Authenticate user and generate tokens

    Returns access token (15 min expiry) and refresh token (7 day expiry).

    - **username**: Username or email
    - **password**: User password

    Rate limit: 10 attempts per 5 minutes per IP address
    """
    # Rate limiting check
    client_ip = get_client_ip(http_request)
    allowed, remaining, retry_after = await redis_service.check_ip_rate_limit(
        ip_address=client_ip,
        endpoint="auth:login",
        limit=LOGIN_RATE_LIMIT,
        window=LOGIN_RATE_WINDOW
    )

    if not allowed:
        logger.warning(
            "Login rate limit exceeded",
            ip=client_ip,
            retry_after=retry_after
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)}
        )

    # Find user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == request.username) | (User.email == request.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("Login failed: user not found", username=request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        logger.warning("Login failed: invalid password", username=request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if hasattr(user, "is_active") and not user.is_active:
        logger.warning("Login failed: inactive user", username=request.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = create_access_token(user.user_id, user.username)
    refresh_token = create_refresh_token(user.user_id, user.username)

    logger.info("User logged in successfully", user_id=str(user.user_id), username=user.username)

    # Build user response
    user_data = UserResponse.model_validate(user)
    if hasattr(user, "is_active"):
        user_data.is_active = user.is_active
    else:
        user_data.is_active = True

    return LoginResponse(
        user=user_data,
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Generate new access token using refresh token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token

    Use refresh token to generate a new access token without re-authenticating.
    Checks Redis blacklist to ensure the refresh token hasn't been revoked.

    - **refresh_token**: Valid JWT refresh token
    """
    try:
        # Verify refresh token (async with Redis blacklist check)
        payload = await verify_token_async(request.refresh_token, expected_type=TokenType.REFRESH)

        user_id_str = payload.get("sub")
        username = payload.get("username")

        if not user_id_str or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Verify user still exists
        from uuid import UUID
        user_id = UUID(user_id_str)
        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("Refresh failed: user not found", user_id=user_id_str)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Check if user is active
        if hasattr(user, "is_active") and not user.is_active:
            logger.warning("Refresh failed: inactive user", user_id=user_id_str)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        # Generate new access token
        access_token = create_access_token(user.user_id, user.username)

        logger.info("Access token refreshed", user_id=user_id_str, username=username)

        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,  # Return same refresh token
        )

    except (JWTError, ValueError) as e:
        logger.warning("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/auth/logout",
    response_model=LogoutResponse,
    summary="User logout",
    description="Invalidate tokens by adding them to blacklist (stored in Redis)",
)
async def logout(
    request: LogoutRequest,
    user: User = Depends(get_current_active_user),
):
    """
    Logout user

    Adds access and/or refresh tokens to Redis blacklist to invalidate them.
    Blacklisted tokens are automatically expired after their natural TTL.

    - **access_token**: Access token to blacklist (optional)
    - **refresh_token**: Refresh token to blacklist (optional)
    """
    # Blacklist tokens in Redis (async)
    if request.access_token:
        # Access tokens expire in 15 minutes, set TTL accordingly
        await blacklist_token_async(request.access_token, ttl_seconds=15 * 60)
        logger.debug("Access token blacklisted in Redis", user_id=str(user.user_id))

    if request.refresh_token:
        # Refresh tokens expire in 7 days, set TTL accordingly
        await blacklist_token_async(request.refresh_token, ttl_seconds=7 * 24 * 60 * 60)
        logger.debug("Refresh token blacklisted in Redis", user_id=str(user.user_id))

    logger.info("User logged out", user_id=str(user.user_id), username=user.username)

    return LogoutResponse()


@router.get(
    "/auth/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user's profile",
)
async def get_current_user_profile(
    user: User = Depends(get_current_active_user),
):
    """
    Get current user profile

    Returns profile information for the authenticated user.
    """
    user_data = UserResponse.model_validate(user)
    if hasattr(user, "is_active"):
        user_data.is_active = user.is_active
    else:
        user_data.is_active = True

    return user_data


@router.post(
    "/auth/change-password",
    response_model=PasswordChangeResponse,
    summary="Change password",
    description="Change current user's password",
)
async def change_password(
    request: PasswordChangeRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change user password

    Requires current password for verification.

    - **current_password**: Current password
    - **new_password**: New password (minimum 8 characters)
    """
    # Verify current password
    if not verify_password(request.current_password, user.password_hash):
        logger.warning("Password change failed: invalid current password", user_id=str(user.user_id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid current password",
        )

    # Update password
    user.password_hash = hash_password(request.new_password)
    await db.commit()

    logger.info("Password changed successfully", user_id=str(user.user_id), username=user.username)

    return PasswordChangeResponse()


@router.get(
    "/auth/public",
    summary="Public endpoint (no auth required)",
    description="Example endpoint demonstrating optional authentication",
)
async def public_endpoint(
    user: Optional[User] = Depends(optional_auth),
):
    """
    Public endpoint with optional authentication

    Returns different data based on whether user is authenticated.
    """
    if user:
        return {
            "message": f"Hello, {user.username}!",
            "authenticated": True,
            "user_id": str(user.user_id),
        }
    else:
        return {
            "message": "Hello, Guest!",
            "authenticated": False,
        }
