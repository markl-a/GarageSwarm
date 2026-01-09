"""
Worker Authentication Dependencies

FastAPI dependencies for Worker API Key authentication.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, WebSocket, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.logging_config import get_logger

logger = get_logger(__name__)

# API Key header scheme for OpenAPI documentation
api_key_header_scheme = APIKeyHeader(
    name="X-Worker-API-Key",
    auto_error=False,
    description="Worker API Key for authentication",
)


async def get_worker_api_key_service(
    db: AsyncSession = Depends(get_db),
):
    """Dependency to get WorkerAPIKeyService instance"""
    # Import here to avoid circular import
    from src.services.worker_api_key_service import WorkerAPIKeyService
    return WorkerAPIKeyService(db)


def extract_api_key(
    x_worker_api_key: Optional[str] = None,
    authorization: Optional[str] = None,
) -> Optional[str]:
    """Extract API key from headers

    Supports:
    - X-Worker-API-Key: {api_key}
    - Authorization: Bearer {api_key} (if key starts with 'wk_')

    Args:
        x_worker_api_key: Value from X-Worker-API-Key header
        authorization: Value from Authorization header

    Returns:
        API key string or None
    """
    # Prefer X-Worker-API-Key header
    if x_worker_api_key:
        return x_worker_api_key

    # Fall back to Authorization header with Bearer prefix
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
        # Check if it's a worker API key (starts with wk_)
        if token.startswith("wk_"):
            return token

    return None


async def require_worker_auth(
    request: Request,
    x_worker_api_key: Optional[str] = Header(None, alias="X-Worker-API-Key"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """
    Require worker API key authentication

    Validates the API key and returns the associated worker_id.

    Args:
        request: FastAPI request object
        x_worker_api_key: X-Worker-API-Key header value
        authorization: Authorization header value
        db: Database session

    Returns:
        UUID of the authenticated worker

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    api_key = extract_api_key(x_worker_api_key, authorization)

    if not api_key:
        client_host = request.client.host if request.client else "unknown"
        logger.warning(
            "Worker auth failed: missing API key",
            path=request.url.path,
            client=client_host,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing worker API key. Provide X-Worker-API-Key header.",
            headers={"WWW-Authenticate": "X-Worker-API-Key"},
        )

    # Import here to avoid circular import
    from src.services.worker_api_key_service import WorkerAPIKeyService
    api_key_service = WorkerAPIKeyService(db)
    worker_id = await api_key_service.validate_api_key(api_key)

    if not worker_id:
        key_prefix = api_key[:12] if len(api_key) >= 12 else "too_short"
        logger.warning(
            "Worker auth failed: invalid API key",
            path=request.url.path,
            key_prefix=key_prefix,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired worker API key",
            headers={"WWW-Authenticate": "X-Worker-API-Key"},
        )

    logger.debug(
        "Worker authenticated",
        worker_id=str(worker_id),
        path=request.url.path,
    )

    return worker_id


async def validate_worker_websocket(
    websocket: WebSocket,
    db: AsyncSession,
) -> Optional[UUID]:
    """
    Validate worker API key for WebSocket connection

    Extracts API key from WebSocket headers or query params.

    Args:
        websocket: WebSocket connection
        db: Database session

    Returns:
        worker_id if valid, None otherwise
    """
    # Import here to avoid circular import
    from src.services.worker_api_key_service import WorkerAPIKeyService
    api_key_service = WorkerAPIKeyService(db)

    # Try headers first
    api_key = extract_api_key(
        x_worker_api_key=websocket.headers.get("x-worker-api-key"),
        authorization=websocket.headers.get("authorization"),
    )

    # Fall back to query parameter (for clients that can't set WS headers)
    if not api_key:
        api_key = websocket.query_params.get("api_key")

    if not api_key:
        logger.warning("WebSocket auth failed: missing API key")
        return None

    worker_id = await api_key_service.validate_api_key(api_key)

    if not worker_id:
        key_prefix = api_key[:12] if len(api_key) >= 12 else "too_short"
        logger.warning(
            "WebSocket auth failed: invalid API key",
            key_prefix=key_prefix,
        )
        return None

    logger.debug(
        "WebSocket worker authenticated",
        worker_id=str(worker_id),
    )

    return worker_id
