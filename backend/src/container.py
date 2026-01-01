"""
Dependency Injection Container

Centralized management of application services and dependencies.
Replaces global state with a testable, injectable container pattern.
"""

from typing import Optional, Callable
from dataclasses import dataclass, field
import asyncio
import structlog

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

logger = structlog.get_logger(__name__)


@dataclass
class AppContainer:
    """
    Application dependency container.

    Holds all shared services and provides a single point of access.
    This pattern improves testability by allowing easy mocking of dependencies.

    Usage:
        # Initialize in lifespan
        container = AppContainer()
        await container.initialize(engine, redis_client, settings)
        set_container(container)

        # Access in dependencies
        container = get_container()
        redis_service = container.redis_service
    """

    # Database
    db_engine: Optional[AsyncEngine] = None
    session_factory: Optional[async_sessionmaker] = None

    # Redis
    redis_client: Optional[object] = None  # RedisClient instance
    redis_service: Optional[object] = None  # RedisService instance

    # Services
    pool_monitor: Optional[object] = None
    worker_health_checker: Optional[object] = None

    # State
    _initialized: bool = field(default=False, repr=False)
    _shutdown: bool = field(default=False, repr=False)

    async def initialize(
        self,
        db_engine: AsyncEngine,
        session_factory: async_sessionmaker,
        redis_client: object,
        redis_service: object,
        settings: object
    ) -> None:
        """
        Initialize all container dependencies.

        Args:
            db_engine: SQLAlchemy async engine
            session_factory: Session factory for creating DB sessions
            redis_client: Redis client instance
            redis_service: Redis service for operations
            settings: Application settings
        """
        if self._initialized:
            logger.warning("Container already initialized, skipping")
            return

        self.db_engine = db_engine
        self.session_factory = session_factory
        self.redis_client = redis_client
        self.redis_service = redis_service

        # Initialize pool monitor
        try:
            from src.services.pool_monitor import PoolMonitor

            self.pool_monitor = PoolMonitor(
                db_engine=db_engine,
                redis_client=redis_client.client if hasattr(redis_client, 'client') else redis_client,
                check_interval=getattr(settings, 'POOL_MONITOR_INTERVAL', 30)
            )
            await self.pool_monitor.start()
            logger.info("Pool monitor initialized via container")
        except Exception as e:
            logger.warning("Pool monitor initialization failed", error=str(e))

        # Initialize worker health checker
        try:
            from src.services.worker_health_checker import WorkerHealthChecker

            self.worker_health_checker = WorkerHealthChecker(
                session_factory=session_factory,
                redis_service=redis_service,
                check_interval=getattr(settings, 'WORKER_HEALTH_CHECK_INTERVAL', 30),
                heartbeat_timeout=getattr(settings, 'WORKER_HEARTBEAT_TIMEOUT', 120)
            )
            await self.worker_health_checker.start()
            logger.info("Worker health checker initialized via container")
        except Exception as e:
            logger.warning("Worker health checker initialization failed", error=str(e))

        self._initialized = True
        logger.info("Container fully initialized")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all container services.
        """
        if self._shutdown:
            return

        logger.info("Shutting down container services")

        # Stop worker health checker
        if self.worker_health_checker:
            try:
                await self.worker_health_checker.stop()
            except Exception as e:
                logger.error("Error stopping worker health checker", error=str(e))

        # Stop pool monitor
        if self.pool_monitor:
            try:
                await self.pool_monitor.stop()
            except Exception as e:
                logger.error("Error stopping pool monitor", error=str(e))

        self._shutdown = True
        logger.info("Container shutdown complete")

    @property
    def is_initialized(self) -> bool:
        """Check if container is initialized."""
        return self._initialized

    @property
    def is_shutdown(self) -> bool:
        """Check if container is shutdown."""
        return self._shutdown


# Global container instance (singleton)
_container: Optional[AppContainer] = None
_container_lock = asyncio.Lock()


def get_container() -> Optional[AppContainer]:
    """
    Get the global container instance.

    Returns:
        AppContainer instance or None if not initialized
    """
    return _container


def set_container(container: AppContainer) -> None:
    """
    Set the global container instance.

    Args:
        container: AppContainer instance to set as global
    """
    global _container
    _container = container
    logger.debug("Global container set")


async def initialize_container(
    db_engine: AsyncEngine,
    session_factory: async_sessionmaker,
    redis_client: object,
    redis_service: object,
    settings: object
) -> AppContainer:
    """
    Initialize and return a new container.

    Thread-safe initialization with lock.

    Args:
        db_engine: SQLAlchemy async engine
        session_factory: Session factory
        redis_client: Redis client
        redis_service: Redis service
        settings: Application settings

    Returns:
        Initialized AppContainer
    """
    global _container

    async with _container_lock:
        if _container and _container.is_initialized:
            logger.warning("Container already exists, returning existing")
            return _container

        container = AppContainer()
        await container.initialize(
            db_engine=db_engine,
            session_factory=session_factory,
            redis_client=redis_client,
            redis_service=redis_service,
            settings=settings
        )

        _container = container
        return container


async def shutdown_container() -> None:
    """
    Shutdown the global container.
    """
    global _container

    if _container:
        await _container.shutdown()
        _container = None


# Dependency injection helpers for FastAPI
def require_container() -> AppContainer:
    """
    FastAPI dependency that requires an initialized container.

    Usage:
        @router.get("/endpoint")
        async def endpoint(container: AppContainer = Depends(require_container)):
            ...

    Raises:
        RuntimeError: If container is not initialized
    """
    container = get_container()
    if not container or not container.is_initialized:
        raise RuntimeError("Application container not initialized")
    return container


def get_redis_service_from_container():
    """
    Get RedisService from container.

    Usage:
        @router.get("/endpoint")
        async def endpoint(redis: RedisService = Depends(get_redis_service_from_container)):
            ...
    """
    container = get_container()
    if not container or not container.redis_service:
        raise RuntimeError("Redis service not available")
    return container.redis_service


def get_pool_monitor_from_container():
    """
    Get PoolMonitor from container.
    """
    container = get_container()
    if container:
        return container.pool_monitor
    return None
