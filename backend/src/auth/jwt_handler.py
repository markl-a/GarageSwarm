"""
JWT Token Handler

Handles creation, verification, and decoding of JWT tokens.
Supports access tokens (15 min) and refresh tokens (7 days).
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
    """Token type enumeration."""
    ACCESS = "access"
    REFRESH = "refresh"


def _hash_token(token: str) -> str:
    """Create SHA256 hash of token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class TokenBlacklist:
    """In-memory token blacklist for logout functionality."""
    _blacklist: set[str] = set()

    @classmethod
    def add(cls, token: str) -> None:
        """Add token to blacklist."""
        token_hash = _hash_token(token)
        cls._blacklist.add(token_hash)
        logger.info("Token added to blacklist", token_hash=token_hash[:16])

    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """Check if token is blacklisted."""
        token_hash = _hash_token(token)
        return token_hash in cls._blacklist

    @classmethod
    def clear(cls) -> None:
        """Clear blacklist (for testing)."""
        cls._blacklist.clear()


# Redis service reference for async operations
_redis_service = None


def set_redis_service(redis_service) -> None:
    """Set Redis service for token blacklist operations."""
    global _redis_service
    _redis_service = redis_service
    logger.info("Redis service configured for token blacklist")


async def blacklist_token_async(token: str, ttl_seconds: Optional[int] = None) -> None:
    """Add token to blacklist using Redis (async)."""
    token_hash = _hash_token(token)

    if ttl_seconds is None:
        ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    if _redis_service:
        try:
            await _redis_service.add_to_blacklist_async(token_hash, ttl_seconds)
            logger.info("Token blacklisted in Redis", token_hash=token_hash[:16])
            return
        except Exception as e:
            logger.warning("Redis blacklist failed, using in-memory fallback", error=str(e))

    TokenBlacklist._blacklist.add(token_hash)
    logger.info("Token blacklisted in-memory (fallback)", token_hash=token_hash[:16])


async def is_token_blacklisted_async(token: str) -> bool:
    """Check if token is blacklisted using Redis (async)."""
    token_hash = _hash_token(token)

    if _redis_service:
        try:
            return await _redis_service.is_blacklisted_async(token_hash)
        except Exception as e:
            logger.warning("Redis blacklist check failed, using in-memory fallback", error=str(e))

    return token_hash in TokenBlacklist._blacklist


def create_access_token(
    user_id: UUID,
    username: str,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create JWT access token.

    Args:
        user_id: User's unique identifier
        username: Username
        additional_claims: Optional additional claims

    Returns:
        Encoded JWT token string
    """
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta

    claims = {
        "sub": str(user_id),
        "username": username,
        "type": TokenType.ACCESS.value,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    if additional_claims:
        claims.update(additional_claims)

    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    logger.debug(
        "Access token created",
        user_id=str(user_id),
        username=username,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    return token


def create_refresh_token(user_id: UUID, username: str) -> str:
    """
    Create JWT refresh token.

    Args:
        user_id: User's unique identifier
        username: Username

    Returns:
        Encoded JWT token string
    """
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
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
        expires_in_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )

    return token


def decode_token(token: str) -> Dict[str, Any]:
    """Decode JWT token without verification."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},
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
    Verify and decode JWT token (synchronous version).

    Args:
        token: JWT token string
        expected_type: Expected token type

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid, expired, or blacklisted
    """
    if TokenBlacklist.is_blacklisted(token):
        logger.warning("Attempt to use blacklisted token")
        raise JWTError("Token has been revoked")

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        if expected_type:
            token_type = payload.get("type")
            if token_type != expected_type.value:
                raise ValueError(f"Expected {expected_type.value} token, got {token_type}")

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
    Verify and decode JWT token (async version with Redis blacklist).

    Args:
        token: JWT token string
        expected_type: Expected token type

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid, expired, or blacklisted
    """
    if await is_token_blacklisted_async(token):
        logger.warning("Attempt to use blacklisted token")
        raise JWTError("Token has been revoked")

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        if expected_type:
            token_type = payload.get("type")
            if token_type != expected_type.value:
                raise ValueError(f"Expected {expected_type.value} token, got {token_type}")

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
    """Add token to blacklist (synchronous, in-memory only)."""
    TokenBlacklist.add(token)
