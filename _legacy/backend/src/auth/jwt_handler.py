"""
JWT Token Handler

Handles creation, verification, and decoding of JWT tokens.
Supports access tokens (15 min) and refresh tokens (7 days).

Token blacklist is stored in Redis for distributed system support.
Falls back to in-memory storage if Redis is unavailable.
"""

import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID

from jose import JWTError, jwt

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)


class TokenType(str, Enum):
    """Token type enumeration"""

    ACCESS = "access"
    REFRESH = "refresh"


def _hash_token(token: str) -> str:
    """
    Create SHA256 hash of token for secure storage

    We store hashes instead of full tokens for security.
    """
    return hashlib.sha256(token.encode()).hexdigest()


class TokenBlacklist:
    """
    In-memory token blacklist for logout functionality (fallback/testing)

    In production, use RedisTokenBlacklist via the async functions.
    This class is kept for backward compatibility and testing.
    """

    _blacklist: set[str] = set()

    @classmethod
    def add(cls, token: str) -> None:
        """Add token to blacklist (stores hash for security)"""
        token_hash = _hash_token(token)
        cls._blacklist.add(token_hash)
        logger.info("Token added to in-memory blacklist", token_hash=token_hash[:16])

    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """Check if token is blacklisted"""
        token_hash = _hash_token(token)
        return token_hash in cls._blacklist

    @classmethod
    def clear(cls) -> None:
        """Clear blacklist (for testing)"""
        cls._blacklist.clear()


# Global reference to Redis service for async operations
_redis_service = None


def set_redis_service(redis_service) -> None:
    """
    Set Redis service for token blacklist operations

    Should be called during application startup after Redis is initialized.

    Args:
        redis_service: RedisService instance
    """
    global _redis_service
    _redis_service = redis_service
    logger.info("Redis service configured for token blacklist")


async def blacklist_token_async(token: str, ttl_seconds: Optional[int] = None) -> None:
    """
    Add token to blacklist using Redis SET structure (async)

    Uses Redis SET for distributed token blacklist with TTL for automatic expiration.
    Falls back to in-memory if Redis is not available.

    Args:
        token: JWT token to blacklist
        ttl_seconds: Optional TTL override (default: 7 days for refresh tokens)
    """
    token_hash = _hash_token(token)

    # Default TTL: 7 days (matches refresh token expiration)
    if ttl_seconds is None:
        ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    if _redis_service:
        try:
            await _redis_service.add_to_blacklist_async(token_hash, ttl_seconds)
            logger.info("Token blacklisted in Redis SET", token_hash=token_hash[:16])
            return
        except Exception as e:
            logger.warning("Redis blacklist failed, using in-memory fallback", error=str(e))

    # Fallback to in-memory
    TokenBlacklist._blacklist.add(token_hash)
    logger.info("Token blacklisted in-memory (fallback)", token_hash=token_hash[:16])


async def is_token_blacklisted_async(token: str) -> bool:
    """
    Check if token is blacklisted using Redis (async)

    Checks Redis SET structure for distributed blacklist.
    Falls back to in-memory check if Redis is not available.

    Args:
        token: JWT token to check

    Returns:
        True if token is blacklisted
    """
    token_hash = _hash_token(token)

    if _redis_service:
        try:
            return await _redis_service.is_blacklisted_async(token_hash)
        except Exception as e:
            logger.warning("Redis blacklist check failed, using in-memory fallback", error=str(e))

    # Fallback to in-memory check
    return token_hash in TokenBlacklist._blacklist


# Alias methods for API consistency
add_to_blacklist_async = blacklist_token_async
is_blacklisted_async = is_token_blacklisted_async


def create_access_token(
    user_id: UUID,
    username: str,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create JWT access token

    Args:
        user_id: User's unique identifier
        username: Username
        additional_claims: Optional additional claims to include in token

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token(
        ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     username="john_doe"
        ... )
    """
    expires_delta = timedelta(minutes=15)  # 15 minutes
    expire = datetime.utcnow() + expires_delta

    claims = {
        "sub": str(user_id),  # Subject (user ID)
        "username": username,
        "type": TokenType.ACCESS.value,
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at
    }

    # Add any additional claims
    if additional_claims:
        claims.update(additional_claims)

    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    logger.debug(
        "Access token created",
        user_id=str(user_id),
        username=username,
        expires_in_minutes=15,
    )

    return token


def create_refresh_token(user_id: UUID, username: str) -> str:
    """
    Create JWT refresh token

    Args:
        user_id: User's unique identifier
        username: Username

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_refresh_token(
        ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     username="john_doe"
        ... )
    """
    expires_delta = timedelta(days=7)  # 7 days
    expire = datetime.utcnow() + expires_delta

    claims = {
        "sub": str(user_id),
        "username": username,
        "type": TokenType.REFRESH.value,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    logger.debug(
        "Refresh token created",
        user_id=str(user_id),
        username=username,
        expires_in_days=7,
    )

    return token


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT token without verification

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is malformed
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},  # Don't verify expiration
        )
        return payload
    except JWTError as e:
        logger.warning("Failed to decode token", error=str(e))
        raise


def verify_token(
    token: str,
    expected_type: Optional[TokenType] = None,
) -> Dict[str, Any]:
    """
    Verify and decode JWT token (synchronous version)

    Note: This version uses in-memory blacklist check.
    For production use with Redis, use verify_token_async instead.

    Args:
        token: JWT token string
        expected_type: Expected token type (access or refresh)

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid, expired, or blacklisted
        ValueError: If token type doesn't match expected type

    Example:
        >>> payload = verify_token(token, TokenType.ACCESS)
        >>> user_id = UUID(payload["sub"])
    """
    # Check if token is blacklisted (in-memory check)
    if TokenBlacklist.is_blacklisted(token):
        logger.warning("Attempt to use blacklisted token")
        raise JWTError("Token has been revoked")

    try:
        # Decode and verify token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Verify token type if specified
        if expected_type:
            token_type = payload.get("type")
            if token_type != expected_type.value:
                logger.warning(
                    "Token type mismatch",
                    expected=expected_type.value,
                    actual=token_type,
                )
                raise ValueError(
                    f"Expected {expected_type.value} token, got {token_type}"
                )

        logger.debug(
            "Token verified successfully",
            user_id=payload.get("sub"),
            token_type=payload.get("type"),
        )

        return payload

    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        raise


async def verify_token_async(
    token: str,
    expected_type: Optional[TokenType] = None,
) -> Dict[str, Any]:
    """
    Verify and decode JWT token (async version with Redis blacklist)

    Uses Redis for distributed blacklist checking.
    Falls back to in-memory if Redis is unavailable.

    Args:
        token: JWT token string
        expected_type: Expected token type (access or refresh)

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid, expired, or blacklisted
        ValueError: If token type doesn't match expected type

    Example:
        >>> payload = await verify_token_async(token, TokenType.ACCESS)
        >>> user_id = UUID(payload["sub"])
    """
    # Check if token is blacklisted (async Redis check with fallback)
    if await is_token_blacklisted_async(token):
        logger.warning("Attempt to use blacklisted token")
        raise JWTError("Token has been revoked")

    try:
        # Decode and verify token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Verify token type if specified
        if expected_type:
            token_type = payload.get("type")
            if token_type != expected_type.value:
                logger.warning(
                    "Token type mismatch",
                    expected=expected_type.value,
                    actual=token_type,
                )
                raise ValueError(
                    f"Expected {expected_type.value} token, got {token_type}"
                )

        logger.debug(
            "Token verified successfully",
            user_id=payload.get("sub"),
            token_type=payload.get("type"),
        )

        return payload

    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        raise


def blacklist_token(token: str) -> None:
    """
    Add token to blacklist (synchronous, in-memory only)

    For production with Redis, use blacklist_token_async instead.

    Args:
        token: JWT token to blacklist

    Example:
        >>> blacklist_token(access_token)
    """
    TokenBlacklist.add(token)
