"""
Worker Health Checker Service

Background service that monitors worker health and handles dead worker cleanup.
Runs periodically to:
1. Detect workers that stopped sending heartbeats
2. Mark them as offline
3. Requeue their in-progress subtasks for reassignment
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import structlog

from src.models.worker import Worker
from src.models.subtask import Subtask
from src.services.redis_service import RedisService
from src.config import settings

logger = structlog.get_logger()


class WorkerHealthChecker:
    """
    Background service for monitoring worker health.

    Responsibilities:
    - Detect workers with stale heartbeats
    - Mark unresponsive workers as offline
    - Requeue orphaned subtasks for reassignment
    - Publish worker status events
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis_service: RedisService,
        check_interval: int = 30,
        heartbeat_timeout: int = 120
    ):
        """
        Initialize WorkerHealthChecker.

        Args:
            session_factory: SQLAlchemy async session factory
            redis_service: Redis service instance
            check_interval: How often to run health checks (seconds)
            heartbeat_timeout: Time since last heartbeat to consider worker dead (seconds)
        """
        self.session_factory = session_factory
        self.redis = redis_service
        self.check_interval = check_interval
        self.heartbeat_timeout = heartbeat_timeout
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background health checker."""
        if self._running:
            logger.warning("Worker health checker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Worker health checker started",
            check_interval=self.check_interval,
            heartbeat_timeout=self.heartbeat_timeout
        )

    async def stop(self) -> None:
        """Stop the background health checker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Worker health checker stopped")

    async def _run_loop(self) -> None:
        """Main loop for periodic health checks."""
        while self._running:
            try:
                await self._check_worker_health()
            except Exception as e:
                logger.error("Error in worker health check", error=str(e))

            await asyncio.sleep(self.check_interval)

    async def _check_worker_health(self) -> None:
        """
        Perform a single health check cycle.

        1. Find workers with stale heartbeats
        2. Mark them as offline
        3. Requeue their subtasks
        """
        async with self.session_factory() as db:
            # Find workers that should be online but have stale heartbeats
            cutoff_time = datetime.utcnow() - timedelta(seconds=self.heartbeat_timeout)

            result = await db.execute(
                select(Worker)
                .where(Worker.status.in_(["online", "busy", "idle"]))
                .where(or_(
                    Worker.last_heartbeat < cutoff_time,
                    Worker.last_heartbeat.is_(None)
                ))
            )
            stale_workers = result.scalars().all()

            if not stale_workers:
                return

            logger.info(
                f"Found {len(stale_workers)} unresponsive worker(s)",
                worker_count=len(stale_workers)
            )

            for worker in stale_workers:
                await self._handle_dead_worker(db, worker)

            await db.commit()

    async def _handle_dead_worker(
        self,
        db: AsyncSession,
        worker: Worker
    ) -> None:
        """
        Handle a worker that appears to be dead.

        Args:
            db: Database session
            worker: Worker instance
        """
        worker_id = worker.worker_id
        old_status = worker.status

        logger.warning(
            "Marking worker as offline",
            worker_id=str(worker_id),
            machine_name=worker.machine_name,
            old_status=old_status,
            last_heartbeat=worker.last_heartbeat.isoformat() if worker.last_heartbeat else None
        )

        # Mark worker as offline
        worker.status = "offline"

        # Find and requeue in-progress subtasks assigned to this worker
        subtask_result = await db.execute(
            select(Subtask)
            .where(Subtask.assigned_worker == worker_id)
            .where(Subtask.status == "in_progress")
        )
        orphaned_subtasks = subtask_result.scalars().all()

        requeued_count = 0
        for subtask in orphaned_subtasks:
            # Reset subtask to pending
            subtask.status = "pending"
            subtask.assigned_worker = None
            subtask.started_at = None

            # Requeue in Redis (atomic operation)
            try:
                await self.redis.atomic_requeue(subtask.subtask_id)
                requeued_count += 1
            except Exception as e:
                # If atomic requeue fails, try manual requeue
                logger.warning(
                    f"Atomic requeue failed, using fallback",
                    subtask_id=str(subtask.subtask_id),
                    error=str(e)
                )
                await self.redis.push_to_queue(subtask.subtask_id)
                await self.redis.remove_from_in_progress(subtask.subtask_id)

        # Update Redis worker status
        try:
            await self.redis.set_worker_status(worker_id, "offline", ttl=3600)
        except Exception as e:
            logger.warning(f"Failed to update Redis worker status: {e}")

        # Publish worker offline event
        try:
            await self.redis.publish_worker_update(worker_id, "offline")
        except Exception as e:
            logger.warning(f"Failed to publish worker offline event: {e}")

        logger.info(
            "Worker marked offline and subtasks requeued",
            worker_id=str(worker_id),
            subtasks_requeued=requeued_count
        )

    async def check_now(self) -> Dict[str, Any]:
        """
        Run an immediate health check (for manual triggering).

        Returns:
            Dict with check results
        """
        async with self.session_factory() as db:
            cutoff_time = datetime.utcnow() - timedelta(seconds=self.heartbeat_timeout)

            # Count workers by status
            result = await db.execute(
                select(Worker.status, Worker.worker_id, Worker.last_heartbeat)
                .where(Worker.status.in_(["online", "busy", "idle"]))
            )
            workers = result.fetchall()

            stale_workers = []
            healthy_workers = []

            for status, worker_id, last_heartbeat in workers:
                if last_heartbeat is None or last_heartbeat < cutoff_time:
                    stale_workers.append({
                        "worker_id": str(worker_id),
                        "status": status,
                        "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else None
                    })
                else:
                    healthy_workers.append({
                        "worker_id": str(worker_id),
                        "status": status,
                        "last_heartbeat": last_heartbeat.isoformat()
                    })

            return {
                "checked_at": datetime.utcnow().isoformat(),
                "heartbeat_timeout_seconds": self.heartbeat_timeout,
                "total_active_workers": len(workers),
                "healthy_workers": len(healthy_workers),
                "stale_workers": len(stale_workers),
                "stale_worker_details": stale_workers
            }


# Global instance for dependency injection
_health_checker: Optional[WorkerHealthChecker] = None


def get_worker_health_checker() -> Optional[WorkerHealthChecker]:
    """Get the global worker health checker instance."""
    return _health_checker


def set_worker_health_checker(checker: WorkerHealthChecker) -> None:
    """Set the global worker health checker instance."""
    global _health_checker
    _health_checker = checker
