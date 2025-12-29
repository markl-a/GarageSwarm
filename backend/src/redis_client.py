"""
Redis Client Configuration

Async Redis client with connection pooling for Multi-Agent platform.
"""

import logging
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client wrapper with connection pooling

    Usage:
        redis_client = RedisClient("redis://localhost:6379/0")
        await redis_client.connect()
        # Use redis_client.client for operations
        await redis_client.close()
    """

    def __init__(self, url: str, max_connections: int = 50):
        """
        Initialize Redis client with connection pool

        Args:
            url: Redis connection URL (redis://host:port/db)
            max_connections: Maximum connections in pool
        """
        self.url = url
        self.max_connections = max_connections
        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """
        Establish connection to Redis server

        Raises:
            redis.ConnectionError: If connection fails
        """
        try:
            # Create connection pool
            self.pool = redis.ConnectionPool.from_url(
                self.url,
                max_connections=self.max_connections,
                decode_responses=True,  # Auto-decode bytes to strings
                socket_timeout=5,  # Socket operation timeout
                socket_connect_timeout=5,  # Connection timeout
                retry_on_timeout=True,  # Retry on timeout
                health_check_interval=30,  # Health check every 30s
            )

            # Create Redis client from pool
            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            await self.client.ping()

            logger.info(f"✓ Redis connected successfully: {self.url}")

        except redis.ConnectionError as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            raise

        except Exception as e:
            logger.error(f"✗ Unexpected error connecting to Redis: {e}")
            raise

    async def close(self) -> None:
        """Close Redis connection and cleanup pool"""
        if self.client:
            try:
                await self.client.close()
                logger.info("Redis client closed")
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")

        if self.pool:
            try:
                await self.pool.disconnect()
                logger.info("Redis connection pool disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Redis pool: {e}")

    async def ping(self) -> bool:
        """
        Test Redis connection

        Returns:
            True if connection is alive, False otherwise
        """
        if not self.client:
            return False

        try:
            await self.client.ping()
            return True
        except redis.ConnectionError:
            return False

    def is_connected(self) -> bool:
        """Check if Redis client is initialized"""
        return self.client is not None

    async def get_info(self) -> dict:
        """
        Get Redis server information

        Returns:
            Dictionary with Redis server info
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")

        info = await self.client.info()
        return {
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "uptime_in_days": info.get("uptime_in_days"),
            "role": info.get("role"),
        }


# Global Redis client instance (initialized in FastAPI lifespan)
redis_client: Optional[RedisClient] = None


def get_redis() -> redis.Redis:
    """
    Dependency injection for Redis client

    Returns:
        Redis client instance

    Raises:
        RuntimeError: If Redis client not initialized
    """
    if not redis_client or not redis_client.client:
        raise RuntimeError(
            "Redis client not initialized. Call redis_client.connect() first."
        )
    return redis_client.client
