"""Analytics Service - System-wide analytics and metrics"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, extract
from sqlalchemy.orm import selectinload
import structlog

from src.models.task import Task
from src.models.subtask import Subtask
from src.models.worker import Worker
from src.services.redis_service import RedisService
from src.schemas.task import TaskStatus
from src.schemas.subtask import SubtaskStatus
from src.schemas.worker import WorkerStatus

logger = structlog.get_logger()


class AnalyticsService:
    """Service for computing system analytics and metrics"""

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        """Initialize AnalyticsService

        Args:
            db: Database session
            redis_service: Optional Redis service for queue metrics
        """
        self.db = db
        self.redis = redis_service

    async def get_task_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive task analytics.

        Returns:
            Dict with task statistics and metrics
        """
        logger.debug("Computing task analytics")

        # Get task counts by status
        status_result = await self.db.execute(
            select(Task.status, func.count())
            .group_by(Task.status)
        )
        by_status = dict(status_result.fetchall())

        # Get total tasks
        total_tasks = sum(by_status.values())

        # Get priority distribution (from task_metadata)
        # Since priority is stored in task_metadata.priority
        priority_counts = {"low": 0, "normal": 0, "high": 0, "urgent": 0}

        priority_result = await self.db.execute(
            select(
                Task.task_metadata["priority"].astext,
                func.count()
            )
            .where(Task.task_metadata["priority"].isnot(None))
            .group_by(Task.task_metadata["priority"].astext)
        )
        for priority, count in priority_result.fetchall():
            if priority in priority_counts:
                priority_counts[priority] = count

        # Count tasks without priority as "normal"
        tasks_with_priority = sum(priority_counts.values())
        priority_counts["normal"] += (total_tasks - tasks_with_priority)

        # Calculate completion rate
        completed = by_status.get("completed", 0)
        failed = by_status.get("failed", 0)
        completion_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0
        failure_rate = (failed / total_tasks * 100) if total_tasks > 0 else 0

        # Calculate average completion time
        avg_time_result = await self.db.execute(
            select(
                func.avg(
                    extract('epoch', Task.completed_at) - extract('epoch', Task.started_at)
                )
            )
            .where(Task.completed_at.isnot(None))
            .where(Task.started_at.isnot(None))
        )
        avg_seconds = avg_time_result.scalar()
        avg_completion_hours = (avg_seconds / 3600) if avg_seconds else None

        # Active and pending counts
        active = by_status.get("in_progress", 0) + by_status.get("initializing", 0)
        pending = by_status.get("pending", 0)

        return {
            "total_tasks": total_tasks,
            "by_status": by_status,
            "by_priority": priority_counts,
            "average_completion_time_hours": round(avg_completion_hours, 2) if avg_completion_hours else None,
            "completion_rate": round(completion_rate, 2),
            "failure_rate": round(failure_rate, 2),
            "active_tasks": active,
            "pending_tasks": pending
        }

    async def get_worker_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive worker analytics.

        Returns:
            Dict with worker statistics and metrics
        """
        logger.debug("Computing worker analytics")

        # Get worker counts by status
        status_result = await self.db.execute(
            select(Worker.status, func.count())
            .group_by(Worker.status)
        )
        by_status = dict(status_result.fetchall())

        total_workers = sum(by_status.values())
        online = by_status.get("online", 0)
        busy = by_status.get("busy", 0)
        idle = by_status.get("idle", 0)

        # Get top performers (workers with most completed subtasks)
        top_performers_result = await self.db.execute(
            select(
                Worker.worker_id,
                Worker.machine_name,
                func.count(Subtask.subtask_id).label('completed_count')
            )
            .join(Subtask, Subtask.assigned_worker == Worker.worker_id)
            .where(Subtask.status == SubtaskStatus.COMPLETED.value)
            .group_by(Worker.worker_id, Worker.machine_name)
            .order_by(func.count(Subtask.subtask_id).desc())
            .limit(5)
        )
        top_performers = [
            {
                "worker_id": str(row.worker_id),
                "machine_name": row.machine_name,
                "completed_tasks": row.completed_count
            }
            for row in top_performers_result.fetchall()
        ]

        # Calculate average tasks per worker
        total_completed = await self.db.execute(
            select(func.count())
            .select_from(Subtask)
            .where(Subtask.status == SubtaskStatus.COMPLETED.value)
        )
        completed_count = total_completed.scalar() or 0
        avg_tasks = (completed_count / total_workers) if total_workers > 0 else 0

        return {
            "total_workers": total_workers,
            "by_status": by_status,
            "online_workers": online,
            "busy_workers": busy,
            "idle_workers": idle,
            "average_tasks_per_worker": round(avg_tasks, 2),
            "top_performers": top_performers
        }

    async def get_subtask_analytics(self) -> Dict[str, int]:
        """
        Get subtask status distribution.

        Returns:
            Dict with subtask counts by status
        """
        result = await self.db.execute(
            select(Subtask.status, func.count())
            .group_by(Subtask.status)
        )
        return dict(result.fetchall())

    async def get_throughput(self, hours: int = 24) -> float:
        """
        Calculate task throughput (completions per hour).

        Args:
            hours: Time window in hours (default: 24)

        Returns:
            Tasks completed per hour
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        result = await self.db.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.completed_at >= cutoff)
            .where(Task.status == TaskStatus.COMPLETED.value)
        )
        completed = result.scalar() or 0

        return round(completed / hours, 2)

    async def get_system_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive system-wide analytics.

        Returns:
            Dict with all analytics data
        """
        logger.info("Computing system analytics")

        # Run analytics queries in parallel
        import asyncio

        task_analytics, worker_analytics, subtask_analytics, throughput = await asyncio.gather(
            self.get_task_analytics(),
            self.get_worker_analytics(),
            self.get_subtask_analytics(),
            self.get_throughput()
        )

        # Get queue length from Redis
        queue_length = 0
        if self.redis:
            try:
                queue_length = await self.redis.get_queue_length()
            except Exception as e:
                logger.warning("Failed to get queue length", error=str(e))

        return {
            "timestamp": datetime.utcnow(),
            "tasks": task_analytics,
            "workers": worker_analytics,
            "subtasks": subtask_analytics,
            "queue_length": queue_length,
            "throughput_per_hour": throughput
        }

    async def get_task_timeline(
        self,
        task_id: UUID,
        include_subtasks: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed timeline for a specific task.

        Args:
            task_id: Task UUID
            include_subtasks: Include subtask timelines

        Returns:
            Dict with task timeline data
        """
        # Get task with subtasks
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.subtasks))
            .where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Build timeline
        timeline = {
            "task_id": str(task_id),
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "status": task.status,
            "progress": task.progress,
            "duration_seconds": None,
            "subtasks": []
        }

        # Calculate duration
        if task.started_at and task.completed_at:
            timeline["duration_seconds"] = (task.completed_at - task.started_at).total_seconds()
        elif task.started_at:
            timeline["duration_seconds"] = (datetime.utcnow() - task.started_at).total_seconds()

        # Add subtask timelines
        if include_subtasks and task.subtasks:
            for subtask in sorted(task.subtasks, key=lambda s: s.created_at or datetime.min):
                subtask_duration = None
                if subtask.started_at and subtask.completed_at:
                    subtask_duration = (subtask.completed_at - subtask.started_at).total_seconds()

                timeline["subtasks"].append({
                    "subtask_id": str(subtask.subtask_id),
                    "name": subtask.name,
                    "status": subtask.status,
                    "started_at": subtask.started_at.isoformat() if subtask.started_at else None,
                    "completed_at": subtask.completed_at.isoformat() if subtask.completed_at else None,
                    "duration_seconds": subtask_duration,
                    "assigned_worker": str(subtask.assigned_worker) if subtask.assigned_worker else None
                })

        return timeline

    async def get_daily_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily task summary for the last N days.

        Args:
            days: Number of days to include

        Returns:
            List of daily summaries
        """
        summaries = []
        end_date = datetime.utcnow().replace(hour=23, minute=59, second=59)
        start_date = end_date - timedelta(days=days - 1)
        start_date = start_date.replace(hour=0, minute=0, second=0)

        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)

            # Get counts for this day
            created_result = await self.db.execute(
                select(func.count())
                .select_from(Task)
                .where(Task.created_at >= day_start)
                .where(Task.created_at < day_end)
            )
            created = created_result.scalar() or 0

            completed_result = await self.db.execute(
                select(func.count())
                .select_from(Task)
                .where(Task.completed_at >= day_start)
                .where(Task.completed_at < day_end)
                .where(Task.status == TaskStatus.COMPLETED.value)
            )
            completed = completed_result.scalar() or 0

            failed_result = await self.db.execute(
                select(func.count())
                .select_from(Task)
                .where(Task.completed_at >= day_start)
                .where(Task.completed_at < day_end)
                .where(Task.status == TaskStatus.FAILED.value)
            )
            failed = failed_result.scalar() or 0

            summaries.append({
                "date": day_start.date().isoformat(),
                "tasks_created": created,
                "tasks_completed": completed,
                "tasks_failed": failed
            })

        return summaries
