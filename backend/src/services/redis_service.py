"""
Redis Service

High-level Redis operations for Multi-Agent platform.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisService:
    """
    High-level Redis service for worker status, task queue, and Pub/Sub

    Provides methods for:
    - Worker status management
    - Task status and progress tracking
    - Task queue operations (FIFO)
    - WebSocket connection management
    - Pub/Sub event broadcasting
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize Redis service

        Args:
            redis_client: Async Redis client instance
        """
        self.redis = redis_client

    # ==================== Worker Status Management ====================

    async def set_worker_status(
        self, worker_id: UUID, status: str, ttl: int = 120
    ) -> None:
        """
        Set worker status with TTL

        Args:
            worker_id: Worker UUID
            status: Worker status (online | offline | busy)
            ttl: Time-to-live in seconds (default: 120s = 2x heartbeat interval)
        """
        await self.redis.setex(f"workers:{worker_id}:status", ttl, status)

        # Maintain online workers set
        if status == "online":
            await self.redis.sadd("workers:online", str(worker_id))
        else:
            await self.redis.srem("workers:online", str(worker_id))

        logger.debug(f"Worker {worker_id} status set to {status}")

    async def get_worker_status(self, worker_id: UUID) -> Optional[str]:
        """
        Get worker status

        Args:
            worker_id: Worker UUID

        Returns:
            Worker status string, or None if not found/expired
        """
        status = await self.redis.get(f"workers:{worker_id}:status")
        return status

    async def get_online_workers(self) -> List[str]:
        """
        Get all online worker IDs

        Returns:
            List of online worker UUIDs as strings
        """
        workers = await self.redis.smembers("workers:online")
        return list(workers)

    async def set_worker_current_task(
        self, worker_id: UUID, task_id: UUID, ttl: int = 600
    ) -> None:
        """
        Set worker's current task

        Args:
            worker_id: Worker UUID
            task_id: Task UUID
            ttl: Time-to-live in seconds (default: 600s = 10 minutes)
        """
        await self.redis.setex(f"workers:{worker_id}:current_task", ttl, str(task_id))

    async def get_worker_current_task(self, worker_id: UUID) -> Optional[str]:
        """
        Get worker's current task ID

        Args:
            worker_id: Worker UUID

        Returns:
            Task UUID as string, or None if no current task
        """
        return await self.redis.get(f"workers:{worker_id}:current_task")

    async def clear_worker_current_task(self, worker_id: UUID) -> None:
        """Clear worker's current task"""
        await self.redis.delete(f"workers:{worker_id}:current_task")

    async def cache_worker_info(
        self, worker_id: UUID, info: Dict[str, Any], ttl: int = 120
    ) -> None:
        """
        Cache worker information

        Args:
            worker_id: Worker UUID
            info: Worker info dict (machine_name, tools, cpu_percent, etc.)
            ttl: Time-to-live in seconds
        """
        # Convert all values to strings for Redis hash
        info_str = {k: str(v) for k, v in info.items()}

        await self.redis.hset(f"workers:{worker_id}:info", mapping=info_str)
        await self.redis.expire(f"workers:{worker_id}:info", ttl)

    async def get_worker_info(self, worker_id: UUID) -> Optional[Dict[str, str]]:
        """
        Get cached worker information

        Args:
            worker_id: Worker UUID

        Returns:
            Worker info dict, or None if not found
        """
        info = await self.redis.hgetall(f"workers:{worker_id}:info")
        return dict(info) if info else None

    # ==================== Task Status & Progress ====================

    async def set_task_status(self, task_id: UUID, status: str) -> None:
        """
        Set task status

        Args:
            task_id: Task UUID
            status: Task status (pending | in_progress | checkpoint | completed | failed)
        """
        await self.redis.set(f"tasks:{task_id}:status", status)
        logger.debug(f"Task {task_id} status set to {status}")

    async def get_task_status(self, task_id: UUID) -> Optional[str]:
        """
        Get task status

        Args:
            task_id: Task UUID

        Returns:
            Task status string, or None if not found
        """
        return await self.redis.get(f"tasks:{task_id}:status")

    async def set_task_progress(self, task_id: UUID, progress: int) -> None:
        """
        Set task progress

        Args:
            task_id: Task UUID
            progress: Progress percentage (0-100)
        """
        await self.redis.set(f"tasks:{task_id}:progress", progress)

    async def get_task_progress(self, task_id: UUID) -> Optional[int]:
        """
        Get task progress

        Args:
            task_id: Task UUID

        Returns:
            Progress percentage, or None if not found
        """
        progress = await self.redis.get(f"tasks:{task_id}:progress")
        return int(progress) if progress else None

    async def increment_task_progress(self, task_id: UUID) -> int:
        """
        Atomically increment task progress by 1

        Args:
            task_id: Task UUID

        Returns:
            New progress value
        """
        new_progress = await self.redis.incr(f"tasks:{task_id}:progress")
        return new_progress

    async def cache_task_metadata(
        self, task_id: UUID, metadata: Dict[str, Any], ttl: int = 3600
    ) -> None:
        """
        Cache task metadata

        Args:
            task_id: Task UUID
            metadata: Task metadata dict
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        metadata_str = {k: str(v) for k, v in metadata.items()}
        await self.redis.hset(f"tasks:{task_id}:cache", mapping=metadata_str)
        await self.redis.expire(f"tasks:{task_id}:cache", ttl)

    async def get_task_metadata(self, task_id: UUID) -> Optional[Dict[str, str]]:
        """Get cached task metadata"""
        metadata = await self.redis.hgetall(f"tasks:{task_id}:cache")
        return dict(metadata) if metadata else None

    async def delete_task_cache(self, task_id: UUID) -> None:
        """Delete all task-related cache on task completion"""
        await self.redis.delete(
            f"tasks:{task_id}:status",
            f"tasks:{task_id}:progress",
            f"tasks:{task_id}:cache",
        )

    # ==================== Task Queue Operations ====================

    async def push_to_queue(self, subtask_id: UUID) -> None:
        """
        Add subtask to pending queue (FIFO)

        Args:
            subtask_id: Subtask UUID
        """
        await self.redis.rpush("task_queue:pending", str(subtask_id))
        logger.debug(f"Subtask {subtask_id} pushed to queue")

    async def pop_from_queue(self) -> Optional[str]:
        """
        Pop subtask from pending queue (FIFO)

        Returns:
            Subtask UUID as string, or None if queue is empty
        """
        subtask_id = await self.redis.lpop("task_queue:pending")
        if subtask_id:
            logger.debug(f"Subtask {subtask_id} popped from queue")
        return subtask_id

    async def get_queue_length(self) -> int:
        """
        Get pending queue length

        Returns:
            Number of subtasks in queue
        """
        return await self.redis.llen("task_queue:pending")

    async def peek_queue(self) -> Optional[str]:
        """
        Peek at next subtask in queue without removing

        Returns:
            Subtask UUID as string, or None if queue is empty
        """
        return await self.redis.lindex("task_queue:pending", 0)

    async def mark_in_progress(self, subtask_id: UUID) -> None:
        """Add subtask to in-progress set"""
        await self.redis.sadd("task_queue:in_progress", str(subtask_id))

    async def remove_from_in_progress(self, subtask_id: UUID) -> None:
        """Remove subtask from in-progress set"""
        await self.redis.srem("task_queue:in_progress", str(subtask_id))

    async def get_in_progress_count(self) -> int:
        """Get count of in-progress subtasks"""
        return await self.redis.scard("task_queue:in_progress")

    # ==================== WebSocket Connection Management ====================

    async def add_websocket_connection(self, client_id: str) -> None:
        """Add WebSocket client to connections set"""
        await self.redis.sadd("websocket:connections", client_id)

    async def remove_websocket_connection(self, client_id: str) -> None:
        """Remove WebSocket client from connections set"""
        await self.redis.srem("websocket:connections", client_id)
        # Clean up subscriptions
        await self.redis.delete(f"websocket:subscriptions:{client_id}")

    async def get_active_connections(self) -> List[str]:
        """Get all active WebSocket client IDs"""
        connections = await self.redis.smembers("websocket:connections")
        return list(connections)

    async def subscribe_to_task(self, client_id: str, task_id: UUID) -> None:
        """Subscribe client to task updates"""
        await self.redis.sadd(f"websocket:subscriptions:{client_id}", str(task_id))
        await self.redis.sadd(f"websocket:task_subscribers:{task_id}", client_id)

    async def unsubscribe_from_task(self, client_id: str, task_id: UUID) -> None:
        """Unsubscribe client from task updates"""
        await self.redis.srem(f"websocket:subscriptions:{client_id}", str(task_id))
        await self.redis.srem(f"websocket:task_subscribers:{task_id}", client_id)

    async def get_task_subscribers(self, task_id: UUID) -> List[str]:
        """Get all clients subscribed to a task"""
        subscribers = await self.redis.smembers(f"websocket:task_subscribers:{task_id}")
        return list(subscribers)

    # ==================== Pub/Sub Event Broadcasting ====================

    async def publish_event(self, channel: str, message: Dict[str, Any]) -> int:
        """
        Publish event to Redis Pub/Sub channel

        Args:
            channel: Channel name (e.g., "events:task_update")
            message: Event message dict (will be JSON-serialized)

        Returns:
            Number of clients that received the message
        """
        message_json = json.dumps(message)
        num_subscribers = await self.redis.publish(channel, message_json)
        logger.debug(f"Published to {channel}: {num_subscribers} subscribers")
        return num_subscribers

    async def subscribe(self, *channels: str) -> redis.client.PubSub:
        """
        Subscribe to Redis Pub/Sub channels

        Args:
            *channels: Channel names to subscribe to

        Returns:
            PubSub object for receiving messages
        """
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*channels)
        logger.info(f"Subscribed to channels: {channels}")
        return pubsub

    async def publish_task_update(
        self, task_id: UUID, status: str, progress: int
    ) -> None:
        """
        Publish task update event

        Args:
            task_id: Task UUID
            status: Task status
            progress: Task progress (0-100)
        """
        from datetime import datetime

        event = {
            "type": "task_update",
            "task_id": str(task_id),
            "status": status,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.publish_event("events:task_update", event)

    async def publish_worker_update(
        self, worker_id: UUID, status: str, resource_usage: Optional[Dict] = None
    ) -> None:
        """
        Publish worker status update event

        Args:
            worker_id: Worker UUID
            status: Worker status
            resource_usage: Optional resource usage dict
        """
        from datetime import datetime

        event = {
            "type": "worker_update",
            "worker_id": str(worker_id),
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if resource_usage:
            event.update(resource_usage)

        await self.publish_event("events:worker_update", event)

    async def publish_subtask_complete(
        self, subtask_id: UUID, task_id: UUID, status: str, evaluation_score: float
    ) -> None:
        """Publish subtask completion event"""
        from datetime import datetime

        event = {
            "type": "subtask_complete",
            "subtask_id": str(subtask_id),
            "task_id": str(task_id),
            "status": status,
            "evaluation_score": evaluation_score,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.publish_event("events:subtask_complete", event)

    async def publish_checkpoint_triggered(
        self, checkpoint_id: UUID, task_id: UUID, reason: str
    ) -> None:
        """Publish checkpoint triggered event"""
        from datetime import datetime

        event = {
            "type": "checkpoint_triggered",
            "checkpoint_id": str(checkpoint_id),
            "task_id": str(task_id),
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.publish_event("events:checkpoint", event)

    # ==================== Distributed Lock ====================

    async def acquire_lock(
        self, resource: str, value: str, ttl: int = 10
    ) -> bool:
        """
        Acquire distributed lock

        Args:
            resource: Resource name to lock
            value: Lock value (usually worker_id or process_id)
            ttl: Lock TTL in seconds

        Returns:
            True if lock acquired, False if already locked
        """
        # SET NX EX returns True if set, False if key exists
        result = await self.redis.set(f"lock:{resource}", value, nx=True, ex=ttl)
        return result is True

    async def release_lock(self, resource: str) -> None:
        """Release distributed lock"""
        await self.redis.delete(f"lock:{resource}")

    # ==================== Rate Limiting ====================

    async def check_rate_limit(
        self, user_id: UUID, endpoint: str, limit: int = 100, window: int = 60
    ) -> bool:
        """
        Check if request is within rate limit

        Args:
            user_id: User UUID
            endpoint: API endpoint
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            True if within limit, False if exceeded
        """
        key = f"ratelimit:{user_id}:{endpoint}"
        count = await self.redis.incr(key)

        if count == 1:
            # First request, set expiration
            await self.redis.expire(key, window)

        return count <= limit

    async def get_rate_limit_remaining(
        self, user_id: UUID, endpoint: str, limit: int = 100
    ) -> int:
        """Get remaining requests in rate limit window"""
        key = f"ratelimit:{user_id}:{endpoint}"
        count = await self.redis.get(key)
        current = int(count) if count else 0
        return max(0, limit - current)
