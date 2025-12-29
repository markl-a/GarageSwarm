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

# Import API routers
from src.api.v1 import health
from src.api.v1 import workers

# Global Redis client
redis_client: RedisClient = None

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

        redis_client = RedisClient(
            settings.REDIS_URL, max_connections=settings.REDIS_MAX_CONNECTIONS
        )
        await redis_client.connect()

        # Set global reference
        import src.redis_client

        src.redis_client.redis_client = redis_client
    except Exception as e:
        logger.error("Failed to initialize Redis", error=str(e))
        raise

    logger.info("✓ All services initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down Multi-Agent on the Web API")

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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled exceptions"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error" if not settings.DEBUG else str(exc),
            "path": request.url.path,
        },
    )


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
app.include_router(workers.router, prefix="/api/v1", tags=["Workers"])
# app.include_router(tasks.router, prefix="/api/v1", tags=["Tasks"])
# app.include_router(subtasks.router, prefix="/api/v1", tags=["Subtasks"])
# app.include_router(checkpoints.router, prefix="/api/v1", tags=["Checkpoints"])
# app.include_router(evaluations.router, prefix="/api/v1", tags=["Evaluations"])

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
