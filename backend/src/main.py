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
from src.middleware.backpressure import BackpressureMiddleware
from src.auth import set_redis_service
from src.services.pool_monitor import PoolMonitor, set_pool_monitor
from src.services.worker_health_checker import (
    WorkerHealthChecker,
    set_worker_health_checker,
    get_worker_health_checker
)

# Import API routers
from src.api.v1 import health
from src.api.v1.health import set_app_start_time
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
from src.api.v1 import diagnostics

# Global Redis client
redis_client: RedisClient = None

# Global pool monitor
pool_monitor: PoolMonitor = None

# Global worker health checker
worker_health_checker: WorkerHealthChecker = None

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

    # Record app start time for uptime tracking
    set_app_start_time()

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

    # Initialize worker health checker
    global worker_health_checker
    try:
        from src.database import async_session_factory

        worker_health_checker = WorkerHealthChecker(
            session_factory=async_session_factory,
            redis_service=redis_service,
            check_interval=settings.WORKER_HEALTH_CHECK_INTERVAL if hasattr(settings, 'WORKER_HEALTH_CHECK_INTERVAL') else 30,
            heartbeat_timeout=settings.WORKER_HEARTBEAT_TIMEOUT if hasattr(settings, 'WORKER_HEARTBEAT_TIMEOUT') else 120
        )
        set_worker_health_checker(worker_health_checker)

        # Start background health checking
        await worker_health_checker.start()
        logger.info("✓ Worker health checker started")
    except Exception as e:
        logger.warning("Worker health checker initialization failed (non-critical)", error=str(e))

    logger.info("✓ All services initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down Multi-Agent on the Web API")

    # Stop worker health checker
    if worker_health_checker:
        await worker_health_checker.stop()

    # Stop pool monitor
    if pool_monitor:
        await pool_monitor.stop()

    # Close Redis connection
    if redis_client:
        await redis_client.close()

    # Close database connection
    await close_db()

    logger.info("✓ Shutdown complete")


# OpenAPI Tags for better documentation organization
openapi_tags = [
    {
        "name": "Health",
        "description": "System health checks and monitoring endpoints",
    },
    {
        "name": "Authentication",
        "description": "User registration, login, and token management",
    },
    {
        "name": "Tasks",
        "description": "Task creation, management, and lifecycle operations",
    },
    {
        "name": "Subtasks",
        "description": "Subtask execution and result submission",
    },
    {
        "name": "Workers",
        "description": "Worker registration, heartbeat, and status management",
    },
    {
        "name": "Checkpoints",
        "description": "Task checkpoints for human review and rollback",
    },
    {
        "name": "Evaluations",
        "description": "Code quality evaluation and scoring",
    },
    {
        "name": "Templates",
        "description": "Reusable workflow templates for common tasks",
    },
    {
        "name": "WebSocket",
        "description": "Real-time communication channels",
    },
    {
        "name": "Metrics",
        "description": "Prometheus metrics endpoint",
    },
    {
        "name": "Mobile UI",
        "description": "Mobile-optimized UI endpoints",
    },
    {
        "name": "Diagnostics",
        "description": "Developer tools for debugging and troubleshooting (DEBUG mode only)",
    },
]

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## Multi-Agent Orchestration Platform

Distributed AI agent orchestration system with:
- **2-3x Speed Boost**: Parallel subtask execution across multiple workers
- **4-Layer Quality Assurance**: Code quality, security, architecture, and testability evaluation
- **Human-in-the-Loop**: Checkpoint-based review system with rollback support

### Quick Start

1. **Register**: `POST /api/v1/auth/register`
2. **Login**: `POST /api/v1/auth/login` → Get JWT token
3. **Create Task**: `POST /api/v1/tasks` with Authorization header
4. **Monitor**: `GET /api/v1/tasks/{id}` or WebSocket `/api/v1/ws/{task_id}`

### Key Features

- **Task Decomposition**: Automatic breakdown into parallelizable subtasks
- **Worker Management**: Dynamic worker registration and load balancing
- **Real-time Updates**: WebSocket and Redis Pub/Sub for live status
- **Batch Operations**: Cancel or update multiple tasks at once
- **Analytics**: System-wide metrics and performance insights

### Authentication

All endpoints (except health checks) require JWT authentication:
```
Authorization: Bearer <your_token>
```
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    openapi_tags=openapi_tags,
    contact={
        "name": "BMAD Support",
        "email": "support@bmad.dev",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Prometheus Metrics Middleware (register first to capture all requests)
app.add_middleware(PrometheusMiddleware)

# Request ID Middleware (for distributed tracing and log correlation)
app.add_middleware(RequestIDMiddleware)

# Backpressure Middleware (reject requests when pools are saturated)
# Excludes health checks and metrics endpoints
app.add_middleware(BackpressureMiddleware)

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
app.include_router(diagnostics.router, prefix="/api/v1", tags=["Diagnostics"])

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
