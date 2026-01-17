"""Worker API Key Service - Business logic for API key management"""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.auth.password import hash_password, verify_password
from src.models.worker_api_key import WorkerAPIKey
from src.models.worker import Worker

logger = structlog.get_logger()

# API key prefix for worker keys
API_KEY_PREFIX = "wk_"
# Length of the random part of the key (in bytes, will be base64 encoded)
API_KEY_BYTES = 36


class WorkerAPIKeyService:
    """Service for managing worker API keys"""

    def __init__(self, db: AsyncSession):
        """Initialize WorkerAPIKeyService

        Args:
            db: Database session
        """
        self.db = db

    def generate_api_key(self) -> Tuple[str, str]:
        """Generate a new API key

        Returns:
            Tuple of (full_key, key_prefix)
        """
        # Generate random key using URL-safe base64
        random_part = secrets.token_urlsafe(API_KEY_BYTES)
        full_key = f"{API_KEY_PREFIX}{random_part}"
        key_prefix = full_key[:12]  # e.g., "wk_a1b2c3d4"
        return full_key, key_prefix

    async def create_api_key(
        self,
        worker_id: UUID,
        created_by: UUID,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[WorkerAPIKey, str]:
        """Create a new API key for a worker

        Args:
            worker_id: Worker UUID
            created_by: User UUID who created the key
            description: Optional description
            expires_in_days: Days until expiration (None = never)

        Returns:
            Tuple of (WorkerAPIKey model, plain_api_key)

        Raises:
            ValueError: If worker not found
        """
        # Verify worker exists
        result = await self.db.execute(
            select(Worker).where(Worker.worker_id == worker_id)
        )
        worker = result.scalar_one_or_none()
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")

        # Generate key
        plain_key, key_prefix = self.generate_api_key()
        key_hash = hash_password(plain_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create model
        api_key = WorkerAPIKey(
            worker_id=worker_id,
            api_key_hash=key_hash,
            key_prefix=key_prefix,
            description=description,
            expires_at=expires_at,
            created_by=created_by,
        )

        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        logger.info(
            "Worker API key created",
            key_id=str(api_key.key_id),
            worker_id=str(worker_id),
            key_prefix=key_prefix,
            created_by=str(created_by),
        )

        return api_key, plain_key

    async def validate_api_key(self, api_key: str) -> Optional[UUID]:
        """Validate an API key and return the associated worker_id

        Args:
            api_key: The plain API key to validate

        Returns:
            worker_id if valid, None otherwise
        """
        # Check prefix
        if not api_key.startswith(API_KEY_PREFIX):
            logger.debug("API key validation failed: invalid prefix")
            return None

        # Extract prefix for faster lookup
        key_prefix = api_key[:12]

        # Find keys with matching prefix that are active
        result = await self.db.execute(
            select(WorkerAPIKey).where(
                WorkerAPIKey.key_prefix == key_prefix,
                WorkerAPIKey.is_active == True,
            )
        )
        keys = result.scalars().all()

        for key in keys:
            # Verify the full key hash
            if verify_password(api_key, key.api_key_hash):
                # Check if still valid (not expired, not revoked)
                if not key.is_valid():
                    logger.warning(
                        "API key expired or revoked",
                        key_id=str(key.key_id),
                        worker_id=str(key.worker_id),
                    )
                    return None

                # Update last_used_at
                key.last_used_at = datetime.utcnow()
                await self.db.commit()

                logger.debug(
                    "API key validated",
                    key_id=str(key.key_id),
                    worker_id=str(key.worker_id),
                )
                return key.worker_id

        logger.debug("API key validation failed: no matching key found")
        return None

    async def list_api_keys(self, worker_id: UUID) -> List[WorkerAPIKey]:
        """List all API keys for a worker

        Args:
            worker_id: Worker UUID

        Returns:
            List of API keys (without hashes)
        """
        result = await self.db.execute(
            select(WorkerAPIKey)
            .where(WorkerAPIKey.worker_id == worker_id)
            .order_by(WorkerAPIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_api_key(self, key_id: UUID) -> Optional[WorkerAPIKey]:
        """Revoke an API key

        Args:
            key_id: API key UUID to revoke

        Returns:
            Updated API key or None if not found
        """
        result = await self.db.execute(
            select(WorkerAPIKey).where(WorkerAPIKey.key_id == key_id)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(api_key)

        logger.info(
            "Worker API key revoked",
            key_id=str(key_id),
            worker_id=str(api_key.worker_id),
        )

        return api_key

    async def get_api_key(self, key_id: UUID) -> Optional[WorkerAPIKey]:
        """Get API key by ID

        Args:
            key_id: API key UUID

        Returns:
            API key or None
        """
        result = await self.db.execute(
            select(WorkerAPIKey).where(WorkerAPIKey.key_id == key_id)
        )
        return result.scalar_one_or_none()
