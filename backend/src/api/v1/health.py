"""
Health Check API

Health check endpoints for monitoring service status.
"""

from fastapi import APIRouter, Depends, HTTPException
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_redis_client
from src.config import get_settings, Settings
from src.logging_config import get_logger
from src.auth.dependencies import require_auth
from src.models.user import User
from src.services.pool_monitor import get_pool_monitor

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
