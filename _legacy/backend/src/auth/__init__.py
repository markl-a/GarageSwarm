"""
Authentication Package

JWT-based authentication for Multi-Agent platform.
Supports distributed token blacklist via Redis.
"""

from .jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_token_async,
    decode_token,
    TokenType,
    blacklist_token,
    blacklist_token_async,
    is_token_blacklisted_async,
    set_redis_service,
)
from .password import verify_password, hash_password
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_auth,
    optional_auth,
)
from .worker_auth import (
    require_worker_auth,
    validate_worker_websocket,
    get_worker_api_key_service,
)

__all__ = [
    # Token creation
    "create_access_token",
    "create_refresh_token",
    # Token verification (sync and async)
    "verify_token",
    "verify_token_async",
    "decode_token",
    "TokenType",
    # Token blacklist (sync and async)
    "blacklist_token",
    "blacklist_token_async",
    "is_token_blacklisted_async",
    "set_redis_service",
    # Password
    "verify_password",
    "hash_password",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "require_auth",
    "optional_auth",
    # Worker authentication
    "require_worker_auth",
    "validate_worker_websocket",
    "get_worker_api_key_service",
]
