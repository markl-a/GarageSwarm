"""
Short-Term Memory System

Redis-based memory for session context and recent events.
Provides fast access to recent task history, worker states, and execution context.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import redis.asyncio as redis
from redis.asyncio import Redis

from .types import (
    MemoryEvent,
    MemoryEventType,
    MemoryItem,
    TaskHistory,
    WorkerStats,
    Feedback,
)

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    Short-term memory using Redis.

    Stores:
    - Recent events (last N or time-based)
    - Task execution history
    - Worker performance stats
    - Active session context
    """

    # Key prefixes
    KEY_EVENTS = "memory:events"
    KEY_TASK_HISTORY = "memory:task:{task_id}"
    KEY_WORKER_STATS = "memory:worker:{worker_id}"
    KEY_SESSION = "memory:session:{session_id}"
    KEY_RECENT = "memory:recent"

    # Defaults
    DEFAULT_TTL = 3600 * 24  # 24 hours
    MAX_RECENT_EVENTS = 1000
    MAX_TASK_EVENTS = 100

    def __init__(self, redis_client: Optional[Redis] = None, redis_url: str = "redis://localhost:6379"):
        """
        Initialize short-term memory.

        Args:
            redis_client: Existing Redis client or None to create new
            redis_url: Redis connection URL
        """
        self._redis: Optional[Redis] = redis_client
        self._redis_url = redis_url
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
        logger.info("Short-term memory connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        self._connected = False
        logger.info("Short-term memory disconnected")

    def _ensure_connected(self) -> None:
        """Ensure Redis is connected."""
        if not self._connected or self._redis is None:
            raise RuntimeError("Short-term memory not connected. Call connect() first.")

    # ==================== Event Storage ====================

    async def store(self, event: MemoryEvent) -> str:
        """
        Store a memory event.

        Args:
            event: The event to store

        Returns:
            Event ID
        """
        self._ensure_connected()

        event_data = event.model_dump_json()
        event_id = event.id

        # Store in recent events list
        await self._redis.lpush(self.KEY_RECENT, event_data)
        await self._redis.ltrim(self.KEY_RECENT, 0, self.MAX_RECENT_EVENTS - 1)

        # Store by task if applicable
        if event.task_id:
            task_key = self.KEY_TASK_HISTORY.format(task_id=str(event.task_id))
            await self._redis.lpush(task_key, event_data)
            await self._redis.ltrim(task_key, 0, self.MAX_TASK_EVENTS - 1)
            await self._redis.expire(task_key, self.DEFAULT_TTL)

        # Update worker stats if applicable
        if event.worker_id:
            await self._update_worker_stats(event)

        logger.debug(f"Stored memory event: {event.event_type} (id: {event_id})")
        return event_id

    async def _update_worker_stats(self, event: MemoryEvent) -> None:
        """Update worker statistics based on event."""
        if not event.worker_id:
            return

        worker_key = self.KEY_WORKER_STATS.format(worker_id=str(event.worker_id))

        # Get existing stats or create new
        existing = await self._redis.get(worker_key)
        if existing:
            stats_data = json.loads(existing)
        else:
            stats_data = {
                "worker_id": str(event.worker_id),
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "avg_execution_time_ms": 0.0,
                "last_active": None,
                "tools_used": {}
            }

        # Update based on event type
        if event.event_type == MemoryEventType.TASK_COMPLETED:
            stats_data["total_tasks"] += 1
            stats_data["successful_tasks"] += 1
            stats_data["last_active"] = datetime.utcnow().isoformat()

            # Update execution time average
            if "execution_time_ms" in event.data:
                old_avg = stats_data["avg_execution_time_ms"]
                count = stats_data["total_tasks"]
                new_time = event.data["execution_time_ms"]
                stats_data["avg_execution_time_ms"] = (
                    (old_avg * (count - 1) + new_time) / count
                )

        elif event.event_type == MemoryEventType.TASK_FAILED:
            stats_data["total_tasks"] += 1
            stats_data["failed_tasks"] += 1
            stats_data["last_active"] = datetime.utcnow().isoformat()

        elif event.event_type == MemoryEventType.TOOL_INVOKED:
            tool = event.data.get("tool", "unknown")
            stats_data["tools_used"][tool] = stats_data["tools_used"].get(tool, 0) + 1

        # Save updated stats
        await self._redis.set(worker_key, json.dumps(stats_data))
        await self._redis.expire(worker_key, self.DEFAULT_TTL * 7)  # Keep for a week

    # ==================== Event Retrieval ====================

    async def get_recent_events(
        self,
        limit: int = 50,
        event_type: Optional[MemoryEventType] = None
    ) -> List[MemoryEvent]:
        """
        Get recent memory events.

        Args:
            limit: Maximum number of events
            event_type: Optional filter by event type

        Returns:
            List of recent events
        """
        self._ensure_connected()

        raw_events = await self._redis.lrange(self.KEY_RECENT, 0, limit * 2)  # Fetch extra for filtering

        events = []
        for raw in raw_events:
            event = MemoryEvent.model_validate_json(raw)
            if event_type is None or event.event_type == event_type:
                events.append(event)
                if len(events) >= limit:
                    break

        return events

    async def get_task_history(self, task_id: UUID) -> TaskHistory:
        """
        Get history for a specific task.

        Args:
            task_id: Task ID

        Returns:
            Task history with all events
        """
        self._ensure_connected()

        task_key = self.KEY_TASK_HISTORY.format(task_id=str(task_id))
        raw_events = await self._redis.lrange(task_key, 0, -1)

        events = [MemoryEvent.model_validate_json(raw) for raw in raw_events]
        events.reverse()  # Oldest first

        history = TaskHistory(task_id=task_id, events=events)

        # Extract additional info from events
        for event in events:
            if event.event_type == MemoryEventType.TASK_STARTED and not history.start_time:
                history.start_time = event.timestamp
            elif event.event_type == MemoryEventType.TASK_COMPLETED:
                history.end_time = event.timestamp
                history.success = True
                history.result = event.data.get("result")
            elif event.event_type == MemoryEventType.TASK_FAILED:
                history.end_time = event.timestamp
                history.success = False
                history.error = event.data.get("error")

        return history

    async def get_worker_performance(self, worker_id: UUID) -> WorkerStats:
        """
        Get performance stats for a worker.

        Args:
            worker_id: Worker ID

        Returns:
            Worker statistics
        """
        self._ensure_connected()

        worker_key = self.KEY_WORKER_STATS.format(worker_id=str(worker_id))
        raw_stats = await self._redis.get(worker_key)

        if raw_stats:
            data = json.loads(raw_stats)
            return WorkerStats(
                worker_id=worker_id,
                total_tasks=data.get("total_tasks", 0),
                successful_tasks=data.get("successful_tasks", 0),
                failed_tasks=data.get("failed_tasks", 0),
                avg_execution_time_ms=data.get("avg_execution_time_ms", 0.0),
                last_active=datetime.fromisoformat(data["last_active"]) if data.get("last_active") else None,
                tools_used=data.get("tools_used", {})
            )

        # Return empty stats for unknown worker
        return WorkerStats(worker_id=worker_id)

    # ==================== Session Context ====================

    async def set_session_context(
        self,
        session_id: str,
        context: Dict[str, Any],
        ttl: int = 3600
    ) -> None:
        """
        Set session context.

        Args:
            session_id: Session identifier
            context: Context data
            ttl: Time to live in seconds
        """
        self._ensure_connected()

        session_key = self.KEY_SESSION.format(session_id=session_id)
        await self._redis.set(session_key, json.dumps(context))
        await self._redis.expire(session_key, ttl)

    async def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session context.

        Args:
            session_id: Session identifier

        Returns:
            Context data or None
        """
        self._ensure_connected()

        session_key = self.KEY_SESSION.format(session_id=session_id)
        raw = await self._redis.get(session_key)

        if raw:
            return json.loads(raw)
        return None

    async def update_session_context(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update session context with new values.

        Args:
            session_id: Session identifier
            updates: Values to update

        Returns:
            Updated context
        """
        context = await self.get_session_context(session_id) or {}
        context.update(updates)
        await self.set_session_context(session_id, context)
        return context

    # ==================== Feedback & Learning ====================

    async def record_feedback(self, feedback: Feedback) -> None:
        """
        Record user feedback for learning.

        Args:
            feedback: Feedback data
        """
        event = MemoryEvent(
            event_type=MemoryEventType.USER_FEEDBACK,
            source="user",
            task_id=feedback.task_id,
            workflow_id=feedback.workflow_id,
            success=feedback.success,
            importance=0.9 if feedback.rating and feedback.rating >= 4 else 0.5,
            data={
                "rating": feedback.rating,
                "comment": feedback.comment
            }
        )
        await self.store(event)

    # ==================== Search ====================

    async def search(
        self,
        query: str,
        limit: int = 10,
        task_id: Optional[UUID] = None
    ) -> List[MemoryItem]:
        """
        Search memory events.

        Simple text-based search for short-term memory.
        For semantic search, use long-term memory (future).

        Args:
            query: Search query
            limit: Maximum results
            task_id: Optional filter by task

        Returns:
            Matching memory items
        """
        self._ensure_connected()

        # Get events to search
        if task_id:
            history = await self.get_task_history(task_id)
            events = history.events
        else:
            events = await self.get_recent_events(limit=limit * 10)

        # Simple text matching
        query_lower = query.lower()
        results = []

        for event in events:
            # Check event type, source, and data for matches
            event_text = f"{event.event_type} {event.source} {json.dumps(event.data)}"

            if query_lower in event_text.lower():
                results.append(MemoryItem(
                    id=event.id,
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    source=event.source,
                    summary=f"{event.event_type}: {event.source}",
                    relevance_score=1.0,
                    data=event.data,
                    metadata={"task_id": str(event.task_id) if event.task_id else None}
                ))

                if len(results) >= limit:
                    break

        return results


# Singleton instance
_memory_instance: Optional[ShortTermMemory] = None


def get_short_term_memory() -> ShortTermMemory:
    """Get the singleton short-term memory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ShortTermMemory()
    return _memory_instance
