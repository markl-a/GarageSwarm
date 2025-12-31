"""
Connection Pool Monitor Service

Monitors database and Redis connection pool health, providing metrics
and alerts for connection pool issues.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
import structlog

from sqlalchemy.ext.asyncio import AsyncEngine
import redis.asyncio as redis

from src.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class PoolMetrics:
    """Connection pool metrics snapshot"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    pool_name: str = ""
    # Pool status
    pool_size: int = 0
    checked_in: int = 0
    checked_out: int = 0
    overflow: int = 0
    max_overflow: int = 0
    # Derived metrics
    utilization_percent: float = 0.0
    available_connections: int = 0
    # Health indicators
    is_healthy: bool = True
    warning_message: Optional[str] = None


@dataclass
class AlertThresholds:
    """Alert threshold configuration"""
    utilization_warning: float = 70.0  # Warn at 70% utilization
    utilization_critical: float = 90.0  # Critical at 90% utilization
    connection_timeout_seconds: float = 5.0  # Connection timeout threshold


class PoolMonitor:
    """
    Connection pool monitoring service.

    Features:
    - Periodic health checks for DB and Redis pools
    - Metrics collection for monitoring
    - Alert callbacks for threshold violations
    - Historical metrics for trending
    """

    def __init__(
        self,
        db_engine: Optional[AsyncEngine] = None,
        redis_client: Optional[redis.Redis] = None,
        check_interval: int = 30,  # seconds
        thresholds: Optional[AlertThresholds] = None
    ):
        """
        Initialize pool monitor.

        Args:
            db_engine: SQLAlchemy async engine (optional)
            redis_client: Redis client instance (optional)
            check_interval: Health check interval in seconds
            thresholds: Alert thresholds configuration
        """
        self.db_engine = db_engine
        self.redis_client = redis_client
        self.check_interval = check_interval
        self.thresholds = thresholds or AlertThresholds()

        # Alert callbacks
        self._alert_callbacks: List[Callable[[str, PoolMetrics], None]] = []

        # Metrics history (last N samples)
        self._metrics_history: Dict[str, List[PoolMetrics]] = {
            "database": [],
            "redis": []
        }
        self._history_max_size = 100

        # Monitor state
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    def register_alert_callback(
        self,
        callback: Callable[[str, PoolMetrics], None]
    ) -> None:
        """
        Register callback for pool alerts.

        Args:
            callback: Function called with (alert_level, metrics) on alerts
        """
        self._alert_callbacks.append(callback)

    async def get_database_metrics(self) -> Optional[PoolMetrics]:
        """
        Get database connection pool metrics.

        Returns:
            PoolMetrics for database pool, or None if not configured
        """
        if not self.db_engine:
            return None

        try:
            pool = self.db_engine.pool

            # SQLAlchemy pool status
            pool_size = pool.size()
            checked_in = pool.checkedin()
            checked_out = pool.checkedout()
            overflow = pool.overflow()

            # Get max_overflow from pool config (if available)
            max_overflow = getattr(pool, '_max_overflow', 0)

            # Calculate utilization
            total_capacity = pool_size + max_overflow
            current_usage = checked_out + overflow
            utilization = (current_usage / total_capacity * 100) if total_capacity > 0 else 0

            metrics = PoolMetrics(
                pool_name="database",
                pool_size=pool_size,
                checked_in=checked_in,
                checked_out=checked_out,
                overflow=overflow,
                max_overflow=max_overflow,
                utilization_percent=round(utilization, 2),
                available_connections=checked_in,
                is_healthy=True
            )

            # Check thresholds and set warnings
            if utilization >= self.thresholds.utilization_critical:
                metrics.is_healthy = False
                metrics.warning_message = f"CRITICAL: Database pool at {utilization:.1f}% utilization"
                await self._trigger_alert("critical", metrics)
            elif utilization >= self.thresholds.utilization_warning:
                metrics.warning_message = f"WARNING: Database pool at {utilization:.1f}% utilization"
                await self._trigger_alert("warning", metrics)

            return metrics

        except Exception as e:
            logger.error("Failed to get database pool metrics", error=str(e))
            return PoolMetrics(
                pool_name="database",
                is_healthy=False,
                warning_message=f"Failed to get metrics: {str(e)}"
            )

    async def get_redis_metrics(self) -> Optional[PoolMetrics]:
        """
        Get Redis connection pool metrics.

        Returns:
            PoolMetrics for Redis pool, or None if not configured
        """
        if not self.redis_client:
            return None

        try:
            # Get Redis connection pool
            pool = self.redis_client.connection_pool

            # Get pool info
            max_connections = pool.max_connections
            # Calculate current connections from pool state
            current_connections = len(pool._in_use_connections) if hasattr(pool, '_in_use_connections') else 0
            available = len(pool._available_connections) if hasattr(pool, '_available_connections') else 0

            # Get Redis server info for additional metrics
            info = await self.redis_client.info('clients')
            connected_clients = info.get('connected_clients', 0)

            # Calculate utilization based on max connections
            utilization = (connected_clients / max_connections * 100) if max_connections > 0 else 0

            metrics = PoolMetrics(
                pool_name="redis",
                pool_size=max_connections,
                checked_in=available,
                checked_out=connected_clients,
                utilization_percent=round(utilization, 2),
                available_connections=max_connections - connected_clients,
                is_healthy=True
            )

            # Check thresholds
            if utilization >= self.thresholds.utilization_critical:
                metrics.is_healthy = False
                metrics.warning_message = f"CRITICAL: Redis pool at {utilization:.1f}% utilization"
                await self._trigger_alert("critical", metrics)
            elif utilization >= self.thresholds.utilization_warning:
                metrics.warning_message = f"WARNING: Redis pool at {utilization:.1f}% utilization"
                await self._trigger_alert("warning", metrics)

            return metrics

        except Exception as e:
            logger.error("Failed to get Redis pool metrics", error=str(e))
            return PoolMetrics(
                pool_name="redis",
                is_healthy=False,
                warning_message=f"Failed to get metrics: {str(e)}"
            )

    async def get_all_metrics(self) -> Dict[str, Optional[PoolMetrics]]:
        """
        Get metrics for all configured pools.

        Returns:
            Dict with metrics for each pool type
        """
        return {
            "database": await self.get_database_metrics(),
            "redis": await self.get_redis_metrics()
        }

    async def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on all pools.

        Returns:
            Dict with health status and any issues found
        """
        metrics = await self.get_all_metrics()

        issues = []
        overall_healthy = True

        for pool_name, pool_metrics in metrics.items():
            if pool_metrics and not pool_metrics.is_healthy:
                overall_healthy = False
                issues.append({
                    "pool": pool_name,
                    "message": pool_metrics.warning_message
                })

        return {
            "healthy": overall_healthy,
            "timestamp": datetime.utcnow().isoformat(),
            "pools": {
                name: {
                    "healthy": m.is_healthy if m else None,
                    "utilization": m.utilization_percent if m else None,
                    "available": m.available_connections if m else None,
                    "warning": m.warning_message if m else None
                }
                for name, m in metrics.items()
            },
            "issues": issues
        }

    async def _trigger_alert(self, level: str, metrics: PoolMetrics) -> None:
        """Trigger alert callbacks"""
        logger.warning(
            f"Pool alert: {level}",
            pool=metrics.pool_name,
            utilization=metrics.utilization_percent,
            message=metrics.warning_message
        )

        for callback in self._alert_callbacks:
            try:
                callback(level, metrics)
            except Exception as e:
                logger.error("Alert callback failed", error=str(e))

    def _store_metrics(self, pool_name: str, metrics: PoolMetrics) -> None:
        """Store metrics in history"""
        history = self._metrics_history.get(pool_name, [])
        history.append(metrics)

        # Trim to max size
        if len(history) > self._history_max_size:
            history = history[-self._history_max_size:]

        self._metrics_history[pool_name] = history

    async def _monitor_loop(self) -> None:
        """Background monitoring loop"""
        while self._running:
            try:
                # Collect metrics
                db_metrics = await self.get_database_metrics()
                if db_metrics:
                    self._store_metrics("database", db_metrics)

                redis_metrics = await self.get_redis_metrics()
                if redis_metrics:
                    self._store_metrics("redis", redis_metrics)

                logger.debug(
                    "Pool metrics collected",
                    db_utilization=db_metrics.utilization_percent if db_metrics else None,
                    redis_utilization=redis_metrics.utilization_percent if redis_metrics else None
                )

            except Exception as e:
                logger.error("Monitor loop error", error=str(e))

            await asyncio.sleep(self.check_interval)

    async def start(self) -> None:
        """Start background monitoring"""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(
            "Pool monitor started",
            check_interval=self.check_interval,
            warning_threshold=self.thresholds.utilization_warning,
            critical_threshold=self.thresholds.utilization_critical
        )

    async def stop(self) -> None:
        """Stop background monitoring"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Pool monitor stopped")

    def get_history(self, pool_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get historical metrics for a pool.

        Args:
            pool_name: Name of the pool (database, redis)
            limit: Maximum number of samples to return

        Returns:
            List of historical metrics dictionaries
        """
        history = self._metrics_history.get(pool_name, [])
        samples = history[-limit:] if limit else history

        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "utilization": m.utilization_percent,
                "checked_out": m.checked_out,
                "available": m.available_connections,
                "healthy": m.is_healthy
            }
            for m in samples
        ]


# Global monitor instance
_pool_monitor: Optional[PoolMonitor] = None


def get_pool_monitor() -> Optional[PoolMonitor]:
    """Get the global pool monitor instance"""
    return _pool_monitor


def set_pool_monitor(monitor: PoolMonitor) -> None:
    """Set the global pool monitor instance"""
    global _pool_monitor
    _pool_monitor = monitor
