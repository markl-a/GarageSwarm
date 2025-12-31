"""
Redis Service

High-level Redis operations for Multi-Agent platform.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
import asyncio

import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

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
        self._max_retries = 3
        self._retry_delay = 0.5  # 500ms base delay

    async def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Execute Redis operation with retry logic

        Args:
            operation: Redis operation to execute
            *args, **kwargs: Arguments for the operation

        Returns:
            Operation result

        Raises:
            RedisError: If all retries fail
        """
        last_error = None
        for attempt in range(self._max_retries):
            try:
                return await operation(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Redis operation failed (attempt {attempt + 1}/{self._max_retries}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Redis operation failed after {self._max_retries} attempts: {e}"
                    )
            except RedisError as e:
                logger.error(f"Redis error: {e}")
                raise

        raise last_error

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

    async def get_multiple_worker_current_tasks(
        self, worker_ids: List[UUID]
    ) -> Dict[str, Optional[str]]:
        """
        Get current tasks for multiple workers in batch using pipeline.

        This is much more efficient than calling get_worker_current_task N times.
        N workers = 1 Redis round-trip instead of N round-trips.

        Args:
            worker_ids: List of worker UUIDs

        Returns:
            Dict mapping worker_id (str) to current_task_id (str or None)
        """
        if not worker_ids:
            return {}

        pipeline = self.redis.pipeline()
        for worker_id in worker_ids:
            pipeline.get(f"workers:{worker_id}:current_task")

        results = await pipeline.execute()

        return {
            str(worker_id): (
                result.decode() if isinstance(result, bytes) else result
            )
            for worker_id, result in zip(worker_ids, results)
        }

    async def get_multiple_worker_statuses(
        self, worker_ids: List[UUID]
    ) -> Dict[str, Optional[str]]:
        """
        Get statuses for multiple workers in batch using pipeline.

        Args:
            worker_ids: List of worker UUIDs

        Returns:
            Dict mapping worker_id (str) to status (str or None)
        """
        if not worker_ids:
            return {}

        pipeline = self.redis.pipeline()
        for worker_id in worker_ids:
            pipeline.get(f"workers:{worker_id}:status")

        results = await pipeline.execute()

        return {
            str(worker_id): (
                result.decode() if isinstance(result, bytes) else result
            )
            for worker_id, result in zip(worker_ids, results)
        }

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

    async def add_task_to_queue(self, task_id: UUID) -> None:
        """
        Add task to main task queue (FIFO)

        Args:
            task_id: Task UUID
        """
        await self.redis.rpush("task_queue:main", str(task_id))
        logger.debug(f"Task {task_id} added to main queue")

    async def remove_task_from_queue(self, task_id: UUID) -> int:
        """
        Remove task from main task queue

        Args:
            task_id: Task UUID

        Returns:
            Number of removed elements
        """
        removed = await self.redis.lrem("task_queue:main", 0, str(task_id))
        logger.debug(f"Task {task_id} removed from main queue: {removed}")
        return removed

    async def get_main_queue_length(self) -> int:
        """
        Get main task queue length

        Returns:
            Number of tasks in main queue
        """
        return await self.redis.llen("task_queue:main")

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

    # Lua script for atomic pop-and-assign operation
    # This prevents race conditions where multiple workers could grab the same subtask
    _ATOMIC_POP_AND_ASSIGN_SCRIPT = """
    -- KEYS[1] = pending queue key
    -- KEYS[2] = in_progress set key
    -- KEYS[3] = worker assignment key pattern prefix
    -- ARGV[1] = worker_id
    -- ARGV[2] = assignment TTL in seconds

    -- Pop from queue
    local subtask_id = redis.call('LPOP', KEYS[1])

    if not subtask_id then
        return nil
    end

    -- Add to in-progress set
    redis.call('SADD', KEYS[2], subtask_id)

    -- Set worker assignment with TTL
    local assignment_key = KEYS[3] .. subtask_id
    redis.call('SETEX', assignment_key, ARGV[2], ARGV[1])

    return subtask_id
    """

    # Lua script for atomic requeue operation
    # Moves subtask back to queue if worker fails
    _ATOMIC_REQUEUE_SCRIPT = """
    -- KEYS[1] = pending queue key
    -- KEYS[2] = in_progress set key
    -- KEYS[3] = assignment key
    -- ARGV[1] = subtask_id

    -- Remove from in-progress
    redis.call('SREM', KEYS[2], ARGV[1])

    -- Delete assignment
    redis.call('DEL', KEYS[3])

    -- Add back to front of queue (high priority requeue)
    redis.call('LPUSH', KEYS[1], ARGV[1])

    return 1
    """

    async def atomic_pop_and_assign(
        self,
        worker_id: UUID,
        assignment_ttl: int = 600
    ) -> Optional[str]:
        """
        Atomically pop a subtask from queue and assign to worker.

        This operation is atomic - no race conditions possible:
        1. Pops subtask from pending queue
        2. Adds to in-progress set
        3. Records worker assignment with TTL

        Args:
            worker_id: Worker UUID to assign subtask to
            assignment_ttl: TTL for assignment record (default: 10 minutes)

        Returns:
            Subtask UUID as string, or None if queue is empty
        """
        try:
            result = await self.redis.eval(
                self._ATOMIC_POP_AND_ASSIGN_SCRIPT,
                3,  # number of keys
                "task_queue:pending",
                "task_queue:in_progress",
                "subtask:assignment:",
                str(worker_id),
                str(assignment_ttl)
            )

            if result:
                subtask_id = result.decode() if isinstance(result, bytes) else result
                logger.debug(
                    f"Atomically assigned subtask {subtask_id} to worker {worker_id}"
                )
                return subtask_id
            return None

        except Exception as e:
            logger.error(f"Atomic pop and assign failed: {e}")
            raise

    async def atomic_requeue(self, subtask_id: UUID) -> bool:
        """
        Atomically requeue a subtask (e.g., when worker fails).

        This operation is atomic:
        1. Removes from in-progress set
        2. Deletes worker assignment
        3. Adds back to front of queue

        Args:
            subtask_id: Subtask UUID to requeue

        Returns:
            True if requeued successfully
        """
        try:
            result = await self.redis.eval(
                self._ATOMIC_REQUEUE_SCRIPT,
                3,  # number of keys
                "task_queue:pending",
                "task_queue:in_progress",
                f"subtask:assignment:{subtask_id}",
                str(subtask_id)
            )

            logger.debug(f"Atomically requeued subtask {subtask_id}")
            return result == 1

        except Exception as e:
            logger.error(f"Atomic requeue failed: {e}")
            raise

    async def get_subtask_assignment(self, subtask_id: UUID) -> Optional[str]:
        """
        Get the worker currently assigned to a subtask.

        Args:
            subtask_id: Subtask UUID

        Returns:
            Worker UUID as string, or None if not assigned
        """
        result = await self.redis.get(f"subtask:assignment:{subtask_id}")
        if result:
            return result.decode() if isinstance(result, bytes) else result
        return None

    async def clear_subtask_assignment(self, subtask_id: UUID) -> None:
        """
        Clear subtask assignment (when subtask completes).

        Args:
            subtask_id: Subtask UUID
        """
        await self.redis.delete(f"subtask:assignment:{subtask_id}")

    async def mark_in_progress(self, subtask_id: UUID) -> None:
        """Add subtask to in-progress set"""
        await self.redis.sadd("task_queue:in_progress", str(subtask_id))

    async def remove_from_in_progress(self, subtask_id: UUID) -> None:
        """Remove subtask from in-progress set"""
        await self.redis.srem("task_queue:in_progress", str(subtask_id))

    async def get_in_progress_count(self) -> int:
        """Get count of in-progress subtasks"""
        return await self.redis.scard("task_queue:in_progress")

    # ==================== Subtask Status Caching ====================

    async def set_subtask_status(
        self, subtask_id: UUID, status: str, ttl: int = 3600
    ) -> None:
        """
        Set subtask status in Redis cache

        Args:
            subtask_id: Subtask UUID
            status: Subtask status
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        await self.redis.setex(f"subtasks:{subtask_id}:status", ttl, status)

    async def get_subtask_status(self, subtask_id: UUID) -> Optional[str]:
        """
        Get subtask status from Redis cache

        Args:
            subtask_id: Subtask UUID

        Returns:
            Subtask status string, or None if not found
        """
        return await self.redis.get(f"subtasks:{subtask_id}:status")

    async def set_subtask_progress(
        self, subtask_id: UUID, progress: int, ttl: int = 3600
    ) -> None:
        """
        Set subtask progress in Redis cache

        Args:
            subtask_id: Subtask UUID
            progress: Progress percentage (0-100)
            ttl: Time-to-live in seconds
        """
        await self.redis.setex(f"subtasks:{subtask_id}:progress", ttl, progress)

    async def get_subtask_progress(self, subtask_id: UUID) -> Optional[int]:
        """
        Get subtask progress from Redis cache

        Args:
            subtask_id: Subtask UUID

        Returns:
            Progress percentage, or None if not found
        """
        progress = await self.redis.get(f"subtasks:{subtask_id}:progress")
        return int(progress) if progress else None

    async def cache_subtask_realtime_data(
        self,
        subtask_id: UUID,
        data: Dict[str, Any],
        ttl: int = 2
    ) -> None:
        """
        Cache subtask real-time data (status, progress) with short TTL

        Args:
            subtask_id: Subtask UUID
            data: Dict with status, progress, etc.
            ttl: Time-to-live in seconds (default: 2s for real-time)
        """
        data_str = {k: str(v) for k, v in data.items()}
        await self.redis.hset(f"subtasks:{subtask_id}:realtime", mapping=data_str)
        await self.redis.expire(f"subtasks:{subtask_id}:realtime", ttl)

    async def get_subtask_realtime_data(
        self, subtask_id: UUID
    ) -> Optional[Dict[str, str]]:
        """
        Get subtask real-time data from cache

        Args:
            subtask_id: Subtask UUID

        Returns:
            Dict with real-time data, or None if not cached
        """
        data = await self.redis.hgetall(f"subtasks:{subtask_id}:realtime")
        return dict(data) if data else None

    async def get_multiple_subtask_statuses(
        self, subtask_ids: List[UUID]
    ) -> Dict[str, Optional[str]]:
        """
        Get multiple subtask statuses in batch

        Args:
            subtask_ids: List of subtask UUIDs

        Returns:
            Dict mapping subtask_id to status (or None if not cached)
        """
        if not subtask_ids:
            return {}

        pipeline = self.redis.pipeline()
        for subtask_id in subtask_ids:
            pipeline.get(f"subtasks:{subtask_id}:status")

        results = await pipeline.execute()

        # Decode bytes to string if needed
        return {
            str(subtask_id): (result.decode() if isinstance(result, bytes) else result)
            for subtask_id, result in zip(subtask_ids, results)
        }

    async def delete_subtask_cache(self, subtask_id: UUID) -> None:
        """Delete all subtask-related cache"""
        await self.redis.delete(
            f"subtasks:{subtask_id}:status",
            f"subtasks:{subtask_id}:progress",
            f"subtasks:{subtask_id}:realtime"
        )

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

    async def publish_websocket_message(self, task_id: UUID, message: Dict[str, Any]) -> int:
        """
        Publish WebSocket message to task channel

        Args:
            task_id: Task UUID
            message: WebSocket message dict (will be JSON-serialized)

        Returns:
            Number of backend instances that received the message
        """
        channel = f"websocket:task:{task_id}"
        message_json = json.dumps(message)
        num_subscribers = await self.redis.publish(channel, message_json)
        logger.debug(f"Published WebSocket message to {channel}: {num_subscribers} subscribers")
        return num_subscribers

    async def subscribe_to_task_channel(self, task_id: UUID, pubsub: redis.client.PubSub) -> None:
        """
        Subscribe to task-specific WebSocket channel

        Args:
            task_id: Task UUID
            pubsub: PubSub object to subscribe with
        """
        channel = f"websocket:task:{task_id}"
        await pubsub.subscribe(channel)
        logger.debug(f"Subscribed to task channel: {channel}")

    async def unsubscribe_from_task_channel(self, task_id: UUID, pubsub: redis.client.PubSub) -> None:
        """
        Unsubscribe from task-specific WebSocket channel

        Args:
            task_id: Task UUID
            pubsub: PubSub object to unsubscribe with
        """
        channel = f"websocket:task:{task_id}"
        await pubsub.unsubscribe(channel)
        logger.debug(f"Unsubscribed from task channel: {channel}")

    # ==================== Message Queue for Offline Clients ====================

    async def queue_message_for_client(
        self, client_id: str, message: Dict[str, Any], ttl: int = 3600
    ) -> None:
        """
        Queue message for offline client

        Args:
            client_id: Client identifier
            message: Message dict to queue
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        queue_key = f"websocket:queue:{client_id}"
        message_json = json.dumps(message)

        # Add to list (FIFO queue)
        await self.redis.rpush(queue_key, message_json)

        # Set TTL on the queue
        await self.redis.expire(queue_key, ttl)

        logger.debug(f"Queued message for offline client: {client_id}")

    async def get_queued_messages(self, client_id: str) -> List[Dict[str, Any]]:
        """
        Get all queued messages for a client

        Args:
            client_id: Client identifier

        Returns:
            List of queued messages
        """
        queue_key = f"websocket:queue:{client_id}"

        # Get all messages from the queue
        messages_json = await self.redis.lrange(queue_key, 0, -1)

        # Delete the queue after retrieval
        if messages_json:
            await self.redis.delete(queue_key)

        # Parse JSON messages
        messages = []
        for msg_json in messages_json:
            try:
                messages.append(json.loads(msg_json))
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse queued message: {msg_json}")

        logger.debug(f"Retrieved {len(messages)} queued messages for client: {client_id}")
        return messages

    async def clear_client_queue(self, client_id: str) -> None:
        """
        Clear message queue for a client

        Args:
            client_id: Client identifier
        """
        queue_key = f"websocket:queue:{client_id}"
        await self.redis.delete(queue_key)
        logger.debug(f"Cleared message queue for client: {client_id}")

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

    # ==================== Query Result Caching ====================

    async def cache_query_result(
        self,
        cache_key: str,
        data: Any,
        ttl: int = 300
    ) -> None:
        """
        Cache database query results with TTL

        Args:
            cache_key: Unique cache key
            data: Data to cache (will be JSON-serialized)
            ttl: Time-to-live in seconds (default: 300s = 5 minutes)
        """
        try:
            # Serialize data to JSON
            data_json = json.dumps(data, default=str)
            await self.redis.setex(f"query_cache:{cache_key}", ttl, data_json)
            logger.debug(f"Cached query result: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache query result: {e}")

    async def get_cached_query(self, cache_key: str) -> Optional[Any]:
        """
        Get cached query result

        Args:
            cache_key: Cache key

        Returns:
            Cached data (deserialized from JSON), or None if not found
        """
        try:
            cached = await self.redis.get(f"query_cache:{cache_key}")
            if cached:
                # Decode bytes if needed
                if isinstance(cached, bytes):
                    cached = cached.decode()
                return json.loads(cached)
            return None
        except Exception as e:
            logger.warning(f"Failed to get cached query: {e}")
            return None

    async def invalidate_cache(self, cache_key: str) -> None:
        """
        Invalidate a specific cache entry

        Args:
            cache_key: Cache key to invalidate
        """
        await self.redis.delete(f"query_cache:{cache_key}")
        logger.debug(f"Invalidated cache: {cache_key}")

    async def invalidate_cache_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching a pattern

        Args:
            pattern: Redis pattern (e.g., "tasks:*", "workers:*")

        Returns:
            Number of keys deleted
        """
        cursor = 0
        deleted = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor,
                match=f"query_cache:{pattern}",
                count=100
            )

            if keys:
                deleted += await self.redis.delete(*keys)

            if cursor == 0:
                break

        logger.debug(f"Invalidated {deleted} cache entries matching: {pattern}")
        return deleted

    async def cache_task_list(
        self,
        status: Optional[str],
        limit: int,
        offset: int,
        tasks_data: List[Dict[str, Any]],
        total: int,
        ttl: int = 300
    ) -> None:
        """
        Cache task list query results

        Args:
            status: Status filter (or None)
            limit: Query limit
            offset: Query offset
            tasks_data: Serialized task data
            total: Total count
            ttl: Time-to-live in seconds
        """
        cache_key = f"tasks_list:{status or 'all'}:{limit}:{offset}"
        cache_data = {
            "tasks": tasks_data,
            "total": total,
            "cached_at": datetime.utcnow().isoformat()
        }
        await self.cache_query_result(cache_key, cache_data, ttl)

    async def get_cached_task_list(
        self,
        status: Optional[str],
        limit: int,
        offset: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached task list query results

        Args:
            status: Status filter (or None)
            limit: Query limit
            offset: Query offset

        Returns:
            Cached task list data, or None if not found
        """
        cache_key = f"tasks_list:{status or 'all'}:{limit}:{offset}"
        return await self.get_cached_query(cache_key)

    async def cache_worker_list(
        self,
        status: Optional[str],
        limit: int,
        offset: int,
        workers_data: List[Dict[str, Any]],
        total: int,
        ttl: int = 300
    ) -> None:
        """
        Cache worker list query results

        Args:
            status: Status filter (or None)
            limit: Query limit
            offset: Query offset
            workers_data: Serialized worker data
            total: Total count
            ttl: Time-to-live in seconds
        """
        cache_key = f"workers_list:{status or 'all'}:{limit}:{offset}"
        cache_data = {
            "workers": workers_data,
            "total": total,
            "cached_at": datetime.utcnow().isoformat()
        }
        await self.cache_query_result(cache_key, cache_data, ttl)

    async def get_cached_worker_list(
        self,
        status: Optional[str],
        limit: int,
        offset: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached worker list query results

        Args:
            status: Status filter (or None)
            limit: Query limit
            offset: Query offset

        Returns:
            Cached worker list data, or None if not found
        """
        cache_key = f"workers_list:{status or 'all'}:{limit}:{offset}"
        return await self.get_cached_query(cache_key)

    async def get_multiple_worker_statuses(
        self,
        worker_ids: List[UUID]
    ) -> Dict[str, Optional[str]]:
        """
        Get multiple worker statuses in batch

        Args:
            worker_ids: List of worker UUIDs

        Returns:
            Dict mapping worker_id to status (or None if not cached)
        """
        if not worker_ids:
            return {}

        pipeline = self.redis.pipeline()
        for worker_id in worker_ids:
            pipeline.get(f"workers:{worker_id}:status")

        results = await pipeline.execute()

        # Decode bytes to string if needed
        return {
            str(worker_id): (result.decode() if isinstance(result, bytes) else result)
            for worker_id, result in zip(worker_ids, results)
        }

    # ==================== Token Blacklist (JWT Logout) ====================

    async def blacklist_token(
        self, token_hash: str, ttl: int = 86400
    ) -> None:
        """
        Add token to blacklist (for logout functionality)

        Uses Redis SET structure with TTL for distributed blacklist.
        Token hash is stored instead of full token for security.
        TTL should match or exceed token expiration time.

        Args:
            token_hash: SHA256 hash of the token
            ttl: Time-to-live in seconds (default: 24 hours)
        """
        # Add to blacklist SET
        await self.redis.sadd("token_blacklist:set", token_hash)

        # Set individual TTL for this token using a separate key
        await self.redis.setex(f"token_blacklist:{token_hash}", ttl, "1")

        logger.debug(f"Token blacklisted (hash: {token_hash[:16]}...)")

    async def is_token_blacklisted(self, token_hash: str) -> bool:
        """
        Check if token is blacklisted

        Args:
            token_hash: SHA256 hash of the token

        Returns:
            True if token is blacklisted, False otherwise
        """
        # Check if token exists in blacklist (using individual key with TTL)
        result = await self.redis.exists(f"token_blacklist:{token_hash}")

        # Clean up from SET if TTL expired
        if result == 0:
            await self.redis.srem("token_blacklist:set", token_hash)

        return result > 0

    async def add_to_blacklist_async(
        self, token_hash: str, ttl: int = 86400
    ) -> None:
        """
        Add token to blacklist using Redis SET structure (async)

        Alias for blacklist_token() for API consistency.
        Uses Redis SET for storage with individual TTLs per token.

        Args:
            token_hash: SHA256 hash of the token
            ttl: Time-to-live in seconds (default: 24 hours)
        """
        await self.blacklist_token(token_hash, ttl)

    async def is_blacklisted_async(self, token_hash: str) -> bool:
        """
        Check if token is blacklisted (async)

        Alias for is_token_blacklisted() for API consistency.

        Args:
            token_hash: SHA256 hash of the token

        Returns:
            True if token is blacklisted, False otherwise
        """
        return await self.is_token_blacklisted(token_hash)

    async def remove_expired_blacklist_entries(self) -> int:
        """
        Clean up expired blacklist entries (manual cleanup if needed)

        Note: Redis TTL handles this automatically, but this can be used
        for explicit cleanup.

        Returns:
            Number of expired entries removed (always 0 with Redis TTL)
        """
        # Redis handles expiration automatically via TTL
        # This method exists for interface compatibility
        return 0

    async def get_blacklist_size(self) -> int:
        """
        Get approximate size of token blacklist

        Returns:
            Number of blacklisted tokens
        """
        cursor = 0
        count = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor,
                match="token_blacklist:*",
                count=100
            )
            count += len(keys)
            if cursor == 0:
                break

        return count

    # ==================== Scheduler Events (Event-Driven Scheduling) ====================

    SCHEDULER_CHANNEL = "scheduler:events"

    async def publish_subtask_completed(self, subtask_id: UUID, task_id: UUID) -> int:
        """
        Publish subtask completion event for event-driven scheduling.

        Instead of polling every N seconds, the scheduler listens for these
        events and triggers allocation immediately when a subtask completes.

        Args:
            subtask_id: Completed subtask UUID
            task_id: Parent task UUID

        Returns:
            Number of subscribers that received the event
        """
        event = {
            "type": "subtask_completed",
            "subtask_id": str(subtask_id),
            "task_id": str(task_id),
            "timestamp": datetime.now().isoformat()
        }
        return await self.publish_event(self.SCHEDULER_CHANNEL, event)

    async def publish_worker_available(self, worker_id: UUID) -> int:
        """
        Publish worker availability event.

        Triggers scheduler to check for pending subtasks when a worker
        becomes available (finished task or came online).

        Args:
            worker_id: Available worker UUID

        Returns:
            Number of subscribers that received the event
        """
        event = {
            "type": "worker_available",
            "worker_id": str(worker_id),
            "timestamp": datetime.now().isoformat()
        }
        return await self.publish_event(self.SCHEDULER_CHANNEL, event)

    async def publish_task_created(self, task_id: UUID) -> int:
        """
        Publish task creation event.

        Triggers scheduler to decompose and schedule the new task.

        Args:
            task_id: New task UUID

        Returns:
            Number of subscribers that received the event
        """
        event = {
            "type": "task_created",
            "task_id": str(task_id),
            "timestamp": datetime.now().isoformat()
        }
        return await self.publish_event(self.SCHEDULER_CHANNEL, event)

    async def subscribe_scheduler_events(self) -> "redis.client.PubSub":
        """
        Subscribe to scheduler events channel.

        Returns:
            PubSub object for receiving scheduler events
        """
        return await self.subscribe(self.SCHEDULER_CHANNEL)
