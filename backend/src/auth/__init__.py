"""
Authentication Module

JWT-based authentication with password hashing.
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

__all__ = [
    "hash_password",
    "verify_password",
    "TokenType",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "verify_token_async",
    "blacklist_token",
    "blacklist_token_async",
    "get_current_user",
    "get_current_active_user",
]
