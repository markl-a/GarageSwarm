"""
Multi-Agent on the Web - FastAPI Backend

Main application entry point with lifespan management, middleware, and routing.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.database import init_db, close_db
from src.logging_config import setup_logging, get_logger
from src.redis_client import RedisClient
from src.middleware.error_handler import register_exception_handlers
from src.middleware.metrics import PrometheusMiddleware
from src.middleware.request_id import RequestIDMiddleware
from src.auth import set_redis_service
from src.services.pool_monitor import PoolMonitor, set_pool_monitor

# Import API routers
from src.api.v1 import health
from src.api.v1 import workers
from src.api.v1 import tasks
from src.api.v1 import subtasks
from src.api.v1 import websocket
from src.api.v1 import checkpoints
from src.api.v1 import evaluations
from src.api.v1 import auth
from src.api.v1 import metrics
from src.api.v1 import templates
from src.api.v1 import mobile_ui

# Global Redis client
redis_client: RedisClient = None

# Global pool monitor
pool_monitor: PoolMonitor = None

# Setup logging
setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Handles startup and shutdown events for database and Redis connections.
    """
    # Startup
    logger.info("🚀 Starting Multi-Agent on the Web API", version=settings.APP_VERSION)

    # Initialize database connection
    try:
        await init_db()
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    # Initialize Redis connection
    global redis_client
    try:
        from src.redis_client import redis_client as rc
        from src.services.redis_service import RedisService

        redis_client = RedisClient(
            settings.REDIS_URL, max_connections=settings.REDIS_MAX_CONNECTIONS
        )
        await redis_client.connect()

        # Set global reference
        import src.redis_client

        src.redis_client.redis_client = redis_client

        # Initialize Redis service for token blacklist
        redis_service = RedisService(redis_client.client)
        set_redis_service(redis_service)
        logger.info("✓ Token blacklist configured with Redis")
    except Exception as e:
        logger.error("Failed to initialize Redis", error=str(e))
        raise

    # Initialize connection pool monitor
    global pool_monitor
    try:
        from src.database import engine

        pool_monitor = PoolMonitor(
            db_engine=engine,
            redis_client=redis_client.client,
            check_interval=settings.POOL_MONITOR_INTERVAL if hasattr(settings, 'POOL_MONITOR_INTERVAL') else 30
        )
        set_pool_monitor(pool_monitor)

        # Start background monitoring
        await pool_monitor.start()
        logger.info("✓ Connection pool monitor started")
    except Exception as e:
        logger.warning("Pool monitor initialization failed (non-critical)", error=str(e))

    logger.info("✓ All services initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down Multi-Agent on the Web API")

    # Stop pool monitor
    if pool_monitor:
        await pool_monitor.stop()

    # Close Redis connection
    if redis_client:
        await redis_client.close()

    # Close database connection
    await close_db()

    logger.info("✓ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Distributed Multi-Agent Orchestration Platform with 2-3x speed boost and 4-layer quality assurance",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Prometheus Metrics Middleware (register first to capture all requests)
app.add_middleware(PrometheusMiddleware)

# Request ID Middleware (for distributed tracing and log correlation)
app.add_middleware(RequestIDMiddleware)

# CORS Middleware - Security hardened configuration
# IMPORTANT: Do NOT use "*" for allow_methods or allow_headers
# Use explicit lists for security compliance
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # From environment variable
    allow_credentials=True,
    # Explicit allowed methods (NOT "*" for security)
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # Explicit allowed headers (NOT "*" for security)
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "X-Requested-With",
        "Accept",
        "Origin",
    ],
    expose_headers=["X-Request-ID"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Register exception handlers
register_exception_handlers(app)


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint

    Returns basic API information.
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled",
        "health": "/api/v1/health",
    }


# API v1 routes
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(workers.router, prefix="/api/v1", tags=["Workers"])
app.include_router(tasks.router, prefix="/api/v1", tags=["Tasks"])
app.include_router(subtasks.router, prefix="/api/v1", tags=["Subtasks"])
app.include_router(websocket.router, prefix="/api/v1", tags=["WebSocket"])
app.include_router(checkpoints.router, prefix="/api/v1", tags=["Checkpoints"])
app.include_router(evaluations.router, prefix="/api/v1", tags=["Evaluations"])
app.include_router(templates.router, prefix="/api/v1", tags=["Templates"])
app.include_router(metrics.router, tags=["Metrics"])
app.include_router(mobile_ui.router, prefix="/mobile", tags=["Mobile UI"])

logger.info("FastAPI application configured", debug=settings.DEBUG)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD or settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
