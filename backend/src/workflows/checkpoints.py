"""
Workflow Checkpoint and Recovery System

Provides checkpoint persistence for workflow state recovery:
- Save workflow state at any point
- Restore from latest or specific checkpoint
- Support for multiple storage backends
- Automatic cleanup of old checkpoints
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import redis.asyncio as redis
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from .state import WorkflowState

logger = logging.getLogger(__name__)


class Checkpoint(BaseModel):
    """
    Represents a workflow checkpoint.

    Contains all information needed to restore a workflow
    to a specific point in its execution.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str
    current_node: Optional[str] = None
    state: Dict[str, Any]  # Serialized WorkflowState
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_json(self) -> str:
        """Serialize checkpoint to JSON string."""
        data = {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "current_node": self.current_node,
            "state": self.state,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "Checkpoint":
        """Deserialize checkpoint from JSON string."""
        data = json.loads(json_str)
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

    def get_workflow_state(self) -> WorkflowState:
        """Convert stored state dict back to WorkflowState."""
        return WorkflowState.from_dict(self.state)


class CheckpointStorageBackend(ABC):
    """
    Abstract base class for checkpoint storage backends.

    Implementations must provide async methods for checkpoint
    storage and retrieval operations.
    """

    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> str:
        """
        Save a checkpoint.

        Args:
            checkpoint: The checkpoint to save

        Returns:
            Checkpoint ID
        """
        pass

    @abstractmethod
    async def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Get a checkpoint by ID.

        Args:
            checkpoint_id: The checkpoint ID

        Returns:
            Checkpoint or None if not found
        """
        pass

    @abstractmethod
    async def get_latest(self, workflow_id: str) -> Optional[Checkpoint]:
        """
        Get the latest checkpoint for a workflow.

        Args:
            workflow_id: The workflow ID

        Returns:
            Latest checkpoint or None if no checkpoints exist
        """
        pass

    @abstractmethod
    async def list(self, workflow_id: str) -> List[Checkpoint]:
        """
        List all checkpoints for a workflow.

        Args:
            workflow_id: The workflow ID

        Returns:
            List of checkpoints ordered by timestamp (newest first)
        """
        pass

    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint.

        Args:
            checkpoint_id: The checkpoint ID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def cleanup(self, workflow_id: str, keep_last_n: int) -> int:
        """
        Clean up old checkpoints, keeping only the last N.

        Args:
            workflow_id: The workflow ID
            keep_last_n: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints deleted
        """
        pass


class RedisCheckpointBackend(CheckpointStorageBackend):
    """
    Redis-based checkpoint storage backend.

    Uses Redis sorted sets for efficient checkpoint ordering
    and retrieval by timestamp.
    """

    # Key patterns
    KEY_CHECKPOINT = "workflow:checkpoint:{checkpoint_id}"
    KEY_WORKFLOW_CHECKPOINTS = "workflow:checkpoints:{workflow_id}"

    # Default TTL for checkpoints (7 days)
    DEFAULT_TTL = 7 * 24 * 3600

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        redis_url: str = "redis://localhost:6379",
        ttl: int = DEFAULT_TTL
    ):
        """
        Initialize Redis checkpoint backend.

        Args:
            redis_client: Existing Redis client or None to create new
            redis_url: Redis connection URL
            ttl: Time to live for checkpoints in seconds
        """
        self._redis: Optional[Redis] = redis_client
        self._redis_url = redis_url
        self._ttl = ttl
        self._connected = False

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        self._connected = True
        logger.info("Checkpoint storage connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        self._connected = False
        logger.info("Checkpoint storage disconnected from Redis")

    def _ensure_connected(self) -> None:
        """Ensure Redis is connected."""
        if not self._connected or self._redis is None:
            raise RuntimeError("Checkpoint storage not connected. Call connect() first.")

    async def save(self, checkpoint: Checkpoint) -> str:
        """Save a checkpoint to Redis."""
        self._ensure_connected()

        checkpoint_key = self.KEY_CHECKPOINT.format(checkpoint_id=checkpoint.id)
        workflow_key = self.KEY_WORKFLOW_CHECKPOINTS.format(workflow_id=checkpoint.workflow_id)

        # Store checkpoint data
        await self._redis.set(checkpoint_key, checkpoint.to_json())
        await self._redis.expire(checkpoint_key, self._ttl)

        # Add to workflow's sorted set (score = timestamp)
        score = checkpoint.timestamp.timestamp()
        await self._redis.zadd(workflow_key, {checkpoint.id: score})
        await self._redis.expire(workflow_key, self._ttl)

        logger.debug(
            f"Saved checkpoint {checkpoint.id} for workflow {checkpoint.workflow_id} "
            f"at node {checkpoint.current_node}"
        )

        return checkpoint.id

    async def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a checkpoint by ID."""
        self._ensure_connected()

        checkpoint_key = self.KEY_CHECKPOINT.format(checkpoint_id=checkpoint_id)
        data = await self._redis.get(checkpoint_key)

        if data:
            return Checkpoint.from_json(data)
        return None

    async def get_latest(self, workflow_id: str) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a workflow."""
        self._ensure_connected()

        workflow_key = self.KEY_WORKFLOW_CHECKPOINTS.format(workflow_id=workflow_id)

        # Get the checkpoint with highest score (most recent)
        results = await self._redis.zrange(workflow_key, -1, -1)

        if not results:
            return None

        checkpoint_id = results[0]
        return await self.get(checkpoint_id)

    async def list(self, workflow_id: str) -> List[Checkpoint]:
        """List all checkpoints for a workflow (newest first)."""
        self._ensure_connected()

        workflow_key = self.KEY_WORKFLOW_CHECKPOINTS.format(workflow_id=workflow_id)

        # Get all checkpoint IDs, sorted by score descending (newest first)
        checkpoint_ids = await self._redis.zrange(workflow_key, 0, -1, desc=True)

        checkpoints = []
        for checkpoint_id in checkpoint_ids:
            checkpoint = await self.get(checkpoint_id)
            if checkpoint:
                checkpoints.append(checkpoint)

        return checkpoints

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        self._ensure_connected()

        # First get the checkpoint to find its workflow_id
        checkpoint = await self.get(checkpoint_id)
        if not checkpoint:
            return False

        checkpoint_key = self.KEY_CHECKPOINT.format(checkpoint_id=checkpoint_id)
        workflow_key = self.KEY_WORKFLOW_CHECKPOINTS.format(workflow_id=checkpoint.workflow_id)

        # Remove from workflow's sorted set
        await self._redis.zrem(workflow_key, checkpoint_id)

        # Delete checkpoint data
        deleted = await self._redis.delete(checkpoint_key)

        if deleted:
            logger.debug(f"Deleted checkpoint {checkpoint_id}")
            return True
        return False

    async def cleanup(self, workflow_id: str, keep_last_n: int) -> int:
        """Clean up old checkpoints, keeping only the last N."""
        self._ensure_connected()

        if keep_last_n < 0:
            raise ValueError("keep_last_n must be non-negative")

        workflow_key = self.KEY_WORKFLOW_CHECKPOINTS.format(workflow_id=workflow_id)

        # Get total count
        total = await self._redis.zcard(workflow_key)

        if total <= keep_last_n:
            return 0

        # Get checkpoints to delete (oldest ones)
        to_delete_count = total - keep_last_n
        checkpoint_ids = await self._redis.zrange(workflow_key, 0, to_delete_count - 1)

        deleted_count = 0
        for checkpoint_id in checkpoint_ids:
            checkpoint_key = self.KEY_CHECKPOINT.format(checkpoint_id=checkpoint_id)

            # Remove from sorted set
            await self._redis.zrem(workflow_key, checkpoint_id)

            # Delete checkpoint data
            await self._redis.delete(checkpoint_key)
            deleted_count += 1

        logger.info(
            f"Cleaned up {deleted_count} old checkpoints for workflow {workflow_id}, "
            f"kept {keep_last_n}"
        )

        return deleted_count


class CheckpointStore:
    """
    High-level checkpoint management interface.

    Provides convenient methods for saving and restoring workflow
    state with support for multiple storage backends.
    """

    def __init__(self, backend: Optional[CheckpointStorageBackend] = None):
        """
        Initialize checkpoint store.

        Args:
            backend: Storage backend to use (defaults to Redis)
        """
        self._backend = backend or RedisCheckpointBackend()

    @property
    def backend(self) -> CheckpointStorageBackend:
        """Get the storage backend."""
        return self._backend

    async def connect(self) -> None:
        """Connect to the storage backend."""
        if isinstance(self._backend, RedisCheckpointBackend):
            await self._backend.connect()

    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        if isinstance(self._backend, RedisCheckpointBackend):
            await self._backend.disconnect()

    async def save_checkpoint(
        self,
        workflow_id: str | UUID,
        state: WorkflowState,
        current_node: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a workflow checkpoint.

        Args:
            workflow_id: The workflow ID
            state: Current workflow state
            current_node: ID of the current node being executed
            metadata: Optional additional metadata

        Returns:
            Checkpoint ID
        """
        # Convert UUID to string if necessary
        workflow_id_str = str(workflow_id) if isinstance(workflow_id, UUID) else workflow_id

        # Serialize workflow state
        state_dict = self._serialize_state(state)

        checkpoint = Checkpoint(
            workflow_id=workflow_id_str,
            current_node=current_node or state.current_node,
            state=state_dict,
            metadata=metadata or {}
        )

        checkpoint_id = await self._backend.save(checkpoint)

        logger.info(
            f"Created checkpoint {checkpoint_id} for workflow {workflow_id_str} "
            f"at node {checkpoint.current_node}"
        )

        return checkpoint_id

    async def get_latest_checkpoint(
        self,
        workflow_id: str | UUID
    ) -> Optional[Checkpoint]:
        """
        Get the latest checkpoint for a workflow.

        Args:
            workflow_id: The workflow ID

        Returns:
            Latest checkpoint or None if no checkpoints exist
        """
        workflow_id_str = str(workflow_id) if isinstance(workflow_id, UUID) else workflow_id
        return await self._backend.get_latest(workflow_id_str)

    async def restore_state(
        self,
        workflow_id: str | UUID,
        checkpoint_id: Optional[str] = None
    ) -> Optional[WorkflowState]:
        """
        Restore workflow state from a checkpoint.

        Args:
            workflow_id: The workflow ID
            checkpoint_id: Specific checkpoint ID (or latest if None)

        Returns:
            Restored WorkflowState or None if no checkpoint found
        """
        if checkpoint_id:
            checkpoint = await self._backend.get(checkpoint_id)
        else:
            workflow_id_str = str(workflow_id) if isinstance(workflow_id, UUID) else workflow_id
            checkpoint = await self._backend.get_latest(workflow_id_str)

        if not checkpoint:
            logger.warning(
                f"No checkpoint found for workflow {workflow_id}"
                + (f" with id {checkpoint_id}" if checkpoint_id else "")
            )
            return None

        state = checkpoint.get_workflow_state()

        logger.info(
            f"Restored workflow {workflow_id} from checkpoint {checkpoint.id} "
            f"at node {checkpoint.current_node}"
        )

        return state

    async def list_checkpoints(
        self,
        workflow_id: str | UUID
    ) -> List[Checkpoint]:
        """
        List all checkpoints for a workflow.

        Args:
            workflow_id: The workflow ID

        Returns:
            List of checkpoints ordered by timestamp (newest first)
        """
        workflow_id_str = str(workflow_id) if isinstance(workflow_id, UUID) else workflow_id
        return await self._backend.list(workflow_id_str)

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a specific checkpoint.

        Args:
            checkpoint_id: The checkpoint ID

        Returns:
            True if deleted, False if not found
        """
        success = await self._backend.delete(checkpoint_id)
        if success:
            logger.info(f"Deleted checkpoint {checkpoint_id}")
        return success

    async def cleanup_old_checkpoints(
        self,
        workflow_id: str | UUID,
        keep_last_n: int = 5
    ) -> int:
        """
        Clean up old checkpoints, keeping only the last N.

        Args:
            workflow_id: The workflow ID
            keep_last_n: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints deleted
        """
        workflow_id_str = str(workflow_id) if isinstance(workflow_id, UUID) else workflow_id
        deleted = await self._backend.cleanup(workflow_id_str, keep_last_n)

        if deleted > 0:
            logger.info(
                f"Cleaned up {deleted} old checkpoints for workflow {workflow_id_str}"
            )

        return deleted

    def _serialize_state(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Serialize WorkflowState to a JSON-compatible dictionary.

        Handles special types like Set and datetime.
        """
        # Use the built-in to_dict method
        base_dict = state.to_dict()

        # Add additional fields not covered by to_dict
        base_dict["parallel_branches"] = {
            k: list(v) for k, v in state.parallel_branches.items()
        }
        base_dict["parallel_results"] = state.parallel_results
        base_dict["loop_iterations"] = state.loop_iterations
        base_dict["pending_reviews"] = state.pending_reviews

        return base_dict


# Singleton instance
_checkpoint_store: Optional[CheckpointStore] = None


def get_checkpoint_store() -> CheckpointStore:
    """Get the singleton checkpoint store instance."""
    global _checkpoint_store
    if _checkpoint_store is None:
        _checkpoint_store = CheckpointStore()
    return _checkpoint_store


async def create_checkpoint_store(
    redis_url: str = "redis://localhost:6379",
    ttl: int = RedisCheckpointBackend.DEFAULT_TTL
) -> CheckpointStore:
    """
    Create and connect a new checkpoint store.

    Args:
        redis_url: Redis connection URL
        ttl: Checkpoint time to live in seconds

    Returns:
        Connected CheckpointStore instance
    """
    backend = RedisCheckpointBackend(redis_url=redis_url, ttl=ttl)
    store = CheckpointStore(backend=backend)
    await store.connect()
    return store
