"""Worker Service - Business logic for worker management"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
import structlog

from src.models.worker import Worker
from src.services.redis_service import RedisService
from src.schemas.worker import WorkerStatus

logger = structlog.get_logger()


class WorkerService:
    """Service for managing worker operations"""

    def __init__(self, db: AsyncSession, redis_service: RedisService):
        """Initialize WorkerService

        Args:
            db: Database session
            redis_service: Redis service instance
        """
        self.db = db
        self.redis = redis_service

    async def register_worker(
        self,
        machine_id: str,
        machine_name: str,
        system_info: dict,
        tools: List[str]
    ) -> Worker:
        """Register a new worker or update existing worker

        This operation is idempotent - if a worker with the same machine_id
        already exists, it will be updated instead of creating a duplicate.

        Args:
            machine_id: Unique machine identifier
            machine_name: Human-readable machine name
            system_info: System information dictionary
            tools: List of available tools

        Returns:
            Worker: Registered or updated worker instance

        Raises:
            Exception: If registration fails
        """
        logger.info(
            "Registering worker",
            machine_id=machine_id,
            machine_name=machine_name,
            tools=tools
        )

        try:
            # Check if worker with this machine_id already exists
            result = await self.db.execute(
                select(Worker).where(Worker.machine_id == machine_id)
            )
            existing_worker = result.scalar_one_or_none()

            if existing_worker:
                # Update existing worker
                logger.info(
                    "Worker already registered, updating",
                    worker_id=str(existing_worker.worker_id),
                    machine_id=machine_id
                )

                existing_worker.machine_name = machine_name
                existing_worker.system_info = system_info
                existing_worker.tools = tools
                existing_worker.status = WorkerStatus.ONLINE.value

                worker = existing_worker
            else:
                # Create new worker
                worker = Worker(
                    machine_id=machine_id,
                    machine_name=machine_name,
                    system_info=system_info,
                    tools=tools,
                    status=WorkerStatus.ONLINE.value
                )
                self.db.add(worker)

            # Commit to database
            await self.db.commit()
            await self.db.refresh(worker)

            # Update Redis status
            await self.redis.set_worker_status(
                worker_id=worker.worker_id,
                status=WorkerStatus.ONLINE.value
            )

            logger.info(
                "Worker registered successfully",
                worker_id=str(worker.worker_id),
                machine_id=machine_id
            )

            return worker

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(
                "Worker registration integrity error",
                machine_id=machine_id,
                error=str(e)
            )
            raise

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Worker registration failed",
                machine_id=machine_id,
                error=str(e)
            )
            raise

    async def update_heartbeat(
        self,
        worker_id: UUID,
        status: str,
        resources: dict,
        current_task: Optional[UUID] = None
    ) -> bool:
        """Update worker heartbeat and status

        Args:
            worker_id: Worker UUID
            status: Worker status (online, busy, idle)
            resources: Resource usage dict (cpu_percent, memory_percent, disk_percent)
            current_task: Currently executing task ID (optional)

        Returns:
            bool: True if update successful

        Raises:
            ValueError: If worker not found
        """
        logger.debug(
            "Updating worker heartbeat",
            worker_id=str(worker_id),
            status=status
        )

        # Get worker from database
        result = await self.db.execute(
            select(Worker).where(Worker.worker_id == worker_id)
        )
        worker = result.scalar_one_or_none()

        if not worker:
            raise ValueError(f"Worker {worker_id} not found")

        # Update worker record
        worker.status = status
        worker.cpu_percent = resources.get("cpu_percent")
        worker.memory_percent = resources.get("memory_percent")
        worker.disk_percent = resources.get("disk_percent")
        worker.last_heartbeat = datetime.utcnow()

        await self.db.commit()

        # Update Redis
        await self.redis.set_worker_status(
            worker_id=worker_id,
            status=status
        )

        if current_task:
            await self.redis.set_worker_current_task(
                worker_id=worker_id,
                task_id=current_task
            )

        return True

    async def get_worker(self, worker_id: UUID) -> Optional[Worker]:
        """Get worker by ID

        Args:
            worker_id: Worker UUID

        Returns:
            Optional[Worker]: Worker instance or None
        """
        result = await self.db.execute(
            select(Worker).where(Worker.worker_id == worker_id)
        )
        return result.scalar_one_or_none()

    async def list_workers(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Worker], int]:
        """List workers with optional filtering

        Args:
            status: Filter by status (optional)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            tuple: (list of workers, total count)
        """
        # Build query
        query = select(Worker)

        if status:
            query = query.where(Worker.status == status)

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(Worker)
        )
        total = count_result.scalar()

        # Get paginated results
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        workers = result.scalars().all()

        return list(workers), total

    async def unregister_worker(self, worker_id: UUID) -> bool:
        """Unregister worker (mark as offline)

        Args:
            worker_id: Worker UUID

        Returns:
            bool: True if successful
        """
        logger.info("Unregistering worker", worker_id=str(worker_id))

        result = await self.db.execute(
            select(Worker).where(Worker.worker_id == worker_id)
        )
        worker = result.scalar_one_or_none()

        if not worker:
            return False

        worker.status = WorkerStatus.OFFLINE.value
        await self.db.commit()

        # Update Redis
        await self.redis.set_worker_status(
            worker_id=worker_id,
            status=WorkerStatus.OFFLINE.value
        )

        logger.info("Worker unregistered", worker_id=str(worker_id))
        return True
