"""
Health Check API

Health check endpoints for monitoring service status.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import redis.asyncio as redis
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_redis_client
from src.config import get_settings, Settings
from src.logging_config import get_logger
from src.auth.dependencies import require_auth
from src.models.user import User
from src.models.task import Task
from src.models.worker import Worker
from src.services.pool_monitor import get_pool_monitor


# Dashboard response schemas
class ServiceStatus(BaseModel):
    """Individual service status"""
    name: str
    status: str = Field(..., description="connected/disconnected/degraded")
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class SystemMetrics(BaseModel):
    """System-level metrics"""
    active_tasks: int = 0
    pending_tasks: int = 0
    online_workers: int = 0
    queue_depth: int = 0


class DashboardResponse(BaseModel):
    """Comprehensive dashboard response"""
    status: str = Field(..., description="healthy/degraded/unhealthy")
    timestamp: datetime
    uptime_seconds: Optional[float] = None
    services: List[ServiceStatus]
    metrics: SystemMetrics
    pools: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


# Track application start time
_app_start_time: Optional[datetime] = None


def set_app_start_time():
    """Set application start time (called from lifespan)"""
    global _app_start_time
    _app_start_time = datetime.utcnow()


def get_uptime_seconds() -> Optional[float]:
    """Get application uptime in seconds"""
    if _app_start_time:
        return (datetime.utcnow() - _app_start_time).total_seconds()
    return None

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
):
    """
    Health check endpoint

    Checks connectivity to:
    - PostgreSQL database
    - Redis cache

    Returns:
        {
            "status": "healthy",
            "database": "connected",
            "redis": "connected"
        }
    """
    health_status = {
        "status": "healthy",
    }

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
        logger.debug("Database health check passed")
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
        logger.error("Database health check failed", error=str(e))

    # Check Redis connection
    try:
        await redis_client.ping()
        health_status["redis"] = "connected"
        logger.debug("Redis health check passed")
    except Exception as e:
        health_status["redis"] = "disconnected"
        health_status["status"] = "unhealthy"
        logger.error("Redis health check failed", error=str(e))

    # Return 503 if any service is unhealthy
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


@router.get("/health/database")
async def database_health(db: AsyncSession = Depends(get_db)):
    """
    Database-specific health check

    Returns:
        {
            "status": "connected",
            "database": "multi_agent_db"
        }
    """
    try:
        result = await db.execute(text("SELECT current_database(), version()"))
        row = result.first()

        return {
            "status": "connected",
            "database": row[0] if row else "unknown",
            "version": row[1].split(",")[0] if row else "unknown",
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={"status": "disconnected", "error": str(e)},
        )


@router.get("/health/redis")
async def redis_health(redis_client: redis.Redis = Depends(get_redis_client)):
    """
    Redis-specific health check

    Returns:
        {
            "status": "connected",
            "redis_version": "7.0.0",
            "connected_clients": 5,
            "used_memory": "1.5M"
        }
    """
    try:
        await redis_client.ping()
        info = await redis_client.info()

        return {
            "status": "connected",
            "redis_version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0),
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={"status": "disconnected", "error": str(e)},
        )


@router.get("/health/detailed")
async def detailed_health(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_auth),
):
    """
    Detailed health check with full system information

    Returns comprehensive health status including:
    - Database connection and version
    - Redis connection and stats
    - Application configuration
    - Environment info
    """
    health_data = {
        "status": "healthy",
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug_mode": settings.DEBUG,
        },
        "services": {},
    }

    # Database health
    try:
        result = await db.execute(text("SELECT current_database(), version()"))
        row = result.first()
        health_data["services"]["database"] = {
            "status": "connected",
            "name": row[0] if row else "unknown",
            "version": row[1].split(",")[0] if row else "unknown",
        }
    except Exception as e:
        health_data["services"]["database"] = {
            "status": "disconnected",
            "error": str(e),
        }
        health_data["status"] = "unhealthy"

    # Redis health
    try:
        await redis_client.ping()
        info = await redis_client.info()
        health_data["services"]["redis"] = {
            "status": "connected",
            "version": info.get("redis_version", "unknown"),
            "clients": info.get("connected_clients", 0),
            "memory": info.get("used_memory_human", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0),
        }
    except Exception as e:
        health_data["services"]["redis"] = {
            "status": "disconnected",
            "error": str(e),
        }
        health_data["status"] = "unhealthy"

    if health_data["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_data)

    return health_data


@router.get("/health/pools")
async def pool_health(
    current_user: User = Depends(require_auth),
):
    """
    Connection pool health check

    Returns health status and utilization for:
    - Database connection pool
    - Redis connection pool

    Includes:
    - Current utilization percentage
    - Available connections
    - Health warnings/alerts
    """
    monitor = get_pool_monitor()

    if not monitor:
        return {
            "status": "unavailable",
            "message": "Pool monitor not initialized"
        }

    health_data = await monitor.check_health()
    return health_data


@router.get("/health/pools/metrics")
async def pool_metrics(
    pool_name: str = None,
    limit: int = 10,
    current_user: User = Depends(require_auth),
):
    """
    Get detailed pool metrics and history

    Args:
        pool_name: Optional filter by pool (database, redis)
        limit: Number of historical samples to return (default: 10)

    Returns:
        Current metrics and historical utilization data
    """
    monitor = get_pool_monitor()

    if not monitor:
        raise HTTPException(
            status_code=503,
            detail={"status": "unavailable", "message": "Pool monitor not initialized"}
        )

    # Get current metrics
    current_metrics = await monitor.get_all_metrics()

    # Build response
    response = {
        "current": {},
        "history": {}
    }

    for name, metrics in current_metrics.items():
        if pool_name and name != pool_name:
            continue

        if metrics:
            response["current"][name] = {
                "pool_size": metrics.pool_size,
                "checked_in": metrics.checked_in,
                "checked_out": metrics.checked_out,
                "overflow": metrics.overflow,
                "utilization_percent": metrics.utilization_percent,
                "available_connections": metrics.available_connections,
                "is_healthy": metrics.is_healthy,
                "warning": metrics.warning_message,
                "timestamp": metrics.timestamp.isoformat()
            }
            response["history"][name] = monitor.get_history(name, limit=limit)

    return response


@router.get("/health/dashboard", response_model=DashboardResponse)
async def health_dashboard(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_auth),
):
    """
    Comprehensive health dashboard

    Aggregates all system health information into a single view:
    - Service connectivity status with latency
    - System metrics (tasks, workers, queue)
    - Connection pool utilization
    - Active warnings and alerts

    Ideal for monitoring dashboards and alerting systems.
    """
    import time

    warnings: List[str] = []
    services: List[ServiceStatus] = []
    overall_status = "healthy"

    # Check database with latency measurement
    db_start = time.perf_counter()
    try:
        result = await db.execute(text("SELECT current_database(), version()"))
        row = result.first()
        db_latency = (time.perf_counter() - db_start) * 1000

        services.append(ServiceStatus(
            name="database",
            status="connected",
            latency_ms=round(db_latency, 2),
            details={
                "database": row[0] if row else "unknown",
                "version": row[1].split(",")[0] if row else "unknown"
            }
        ))

        if db_latency > 100:
            warnings.append(f"Database latency high: {db_latency:.0f}ms")
            overall_status = "degraded"
    except Exception as e:
        services.append(ServiceStatus(
            name="database",
            status="disconnected",
            details={"error": str(e)}
        ))
        overall_status = "unhealthy"
        warnings.append(f"Database disconnected: {str(e)[:100]}")

    # Check Redis with latency measurement
    redis_start = time.perf_counter()
    try:
        await redis_client.ping()
        info = await redis_client.info()
        redis_latency = (time.perf_counter() - redis_start) * 1000

        services.append(ServiceStatus(
            name="redis",
            status="connected",
            latency_ms=round(redis_latency, 2),
            details={
                "version": info.get("redis_version", "unknown"),
                "clients": info.get("connected_clients", 0),
                "memory": info.get("used_memory_human", "unknown"),
                "uptime_days": info.get("uptime_in_days", 0)
            }
        ))

        if redis_latency > 50:
            warnings.append(f"Redis latency high: {redis_latency:.0f}ms")
            if overall_status == "healthy":
                overall_status = "degraded"
    except Exception as e:
        services.append(ServiceStatus(
            name="redis",
            status="disconnected",
            details={"error": str(e)}
        ))
        overall_status = "unhealthy"
        warnings.append(f"Redis disconnected: {str(e)[:100]}")

    # Get system metrics
    metrics = SystemMetrics()
    try:
        # Active tasks (in_progress + initializing)
        active_result = await db.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.status.in_(["in_progress", "initializing"]))
        )
        metrics.active_tasks = active_result.scalar() or 0

        # Pending tasks
        pending_result = await db.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.status == "pending")
        )
        metrics.pending_tasks = pending_result.scalar() or 0

        # Online workers
        online_result = await db.execute(
            select(func.count())
            .select_from(Worker)
            .where(Worker.status.in_(["online", "busy", "idle"]))
        )
        metrics.online_workers = online_result.scalar() or 0

        # Queue depth from Redis
        try:
            queue_len = await redis_client.llen("task_queue")
            metrics.queue_depth = queue_len or 0
        except Exception:
            pass
    except Exception as e:
        logger.warning("Failed to fetch system metrics", error=str(e))
        warnings.append("Could not fetch some system metrics")

    # Get pool metrics
    pools: Dict[str, Any] = {}
    monitor = get_pool_monitor()
    if monitor:
        try:
            pool_health = await monitor.check_health()
            pools = pool_health.get("pools", {})

            # Add pool warnings
            for pool_name, pool_data in pools.items():
                if not pool_data.get("is_healthy", True):
                    warning = pool_data.get("warning", f"{pool_name} pool unhealthy")
                    warnings.append(warning)
                    if overall_status == "healthy":
                        overall_status = "degraded"
        except Exception as e:
            logger.warning("Failed to get pool metrics", error=str(e))

    return DashboardResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        uptime_seconds=get_uptime_seconds(),
        services=services,
        metrics=metrics,
        pools=pools,
        warnings=warnings
    )
