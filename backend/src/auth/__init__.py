"""
Authentication Module

JWT-based authentication with password hashing.
Worker API key authentication for worker agents.
"""

from .password import hash_password, verify_password
from .jwt_handler import (
    TokenType,
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_token_async,
    blacklist_token,
    blacklist_token_async,
)
from .dependencies import get_current_user, get_current_active_user
from .worker_auth import (
    generate_worker_api_key,
    verify_worker_api_key,
    get_optional_worker,
)

__all__ = [
    # Password utilities
    "hash_password",
    "verify_password",
    # JWT tokens
    "TokenType",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "verify_token_async",
    "blacklist_token",
    "blacklist_token_async",
    # User authentication dependencies
    "get_current_user",
    "get_current_active_user",
    # Worker authentication
    "generate_worker_api_key",
    "verify_worker_api_key",
    "get_optional_worker",
]
