"""
Worker Authentication

API key-based authentication for worker agents.
"""

import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.worker import Worker
from src.logging_config import get_logger

logger = get_logger(__name__)


def generate_worker_api_key(prefix: str = "gsw") -> str:
    """
    Generate a secure API key for worker authentication.

    Args:
        prefix: Optional prefix for the key (default: "gsw" for GarageSwarm Worker)

    Returns:
        A secure random API key string (64 characters including prefix)

    Example:
        >>> key = generate_worker_api_key()
        >>> # Returns: "gsw_a1b2c3d4e5f6..." (64 chars total)
    """
    # Generate 32 bytes = 64 hex characters
    # With prefix "gsw_", total length is around 68 characters
    random_part = secrets.token_hex(28)  # 56 hex chars
    return f"{prefix}_{random_part}"


async def verify_worker_api_key(
    x_worker_api_key: str = Header(..., alias="X-Worker-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Worker:
    """
    Verify worker API key from X-Worker-API-Key header.

    Args:
        x_worker_api_key: API key from X-Worker-API-Key header
        db: Database session

    Returns:
        Worker object if valid and active

    Raises:
        HTTPException 401: If API key is invalid or worker not found
        HTTPException 403: If worker is deactivated
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid worker API key",
        headers={"WWW-Authenticate": "X-Worker-API-Key"},
    )

    if not x_worker_api_key:
        logger.warning("Worker authentication failed: missing API key")
        raise credentials_exception

    # Query worker by API key
    result = await db.execute(
        select(Worker).where(Worker.api_key == x_worker_api_key)
    )
    worker = result.scalar_one_or_none()

    if worker is None:
        logger.warning(
            "Worker authentication failed: invalid API key",
            api_key_prefix=x_worker_api_key[:10] + "..." if len(x_worker_api_key) > 10 else "***",
        )
        raise credentials_exception

    # Check if worker is active
    if not worker.is_active:
        logger.warning(
            "Worker authentication failed: worker deactivated",
            worker_id=str(worker.worker_id),
            machine_name=worker.machine_name,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker has been deactivated",
        )

    logger.debug(
        "Worker authenticated successfully",
        worker_id=str(worker.worker_id),
        machine_name=worker.machine_name,
    )

    return worker


async def get_optional_worker(
    x_worker_api_key: Optional[str] = Header(None, alias="X-Worker-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[Worker]:
    """
    Get worker if API key is provided and valid, None otherwise.

    Useful for endpoints that can work with or without worker authentication.

    Args:
        x_worker_api_key: Optional API key from X-Worker-API-Key header
        db: Database session

    Returns:
        Worker object if valid, None if no key provided or invalid
    """
    if not x_worker_api_key:
        return None

    try:
        result = await db.execute(
            select(Worker).where(Worker.api_key == x_worker_api_key)
        )
        worker = result.scalar_one_or_none()

        if worker is None or not worker.is_active:
            return None

        return worker

    except Exception as e:
        logger.warning("Optional worker auth failed", error=str(e))
        return None
