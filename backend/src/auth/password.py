"""
Password Hashing Utilities

Secure password hashing using bcrypt via passlib.
"""

from passlib.context import CryptContext

from src.logging_config import get_logger

logger = get_logger(__name__)

# Create password context for bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password string

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> print(hashed)
        $2b$12$...
    """
    hashed = pwd_context.hash(password)
    logger.debug("Password hashed successfully")
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise

    Example:
        >>> is_valid = verify_password("my_password", stored_hash)
        >>> if is_valid:
        ...     print("Password is correct")
    """
    is_valid = pwd_context.verify(plain_password, hashed_password)

    if is_valid:
        logger.debug("Password verification successful")
    else:
        logger.debug("Password verification failed")

    return is_valid
