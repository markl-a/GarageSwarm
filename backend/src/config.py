"""
Application Configuration

Environment variable management using Pydantic Settings.
"""

import secrets
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "GarageSwarm"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres_dev_password@localhost:5432/multi_agent_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY security requirements."""
        import os
        environment = os.getenv("ENVIRONMENT", "development").lower()

        if not v:
            if environment in ("production", "staging"):
                raise ValueError(
                    "SECRET_KEY environment variable is required in production/staging."
                )
            import warnings
            warnings.warn(
                "SECRET_KEY not set - using random key. Sessions will be invalidated on restart.",
                UserWarning
            )
            return secrets.token_urlsafe(32)

        if len(v) < 32 and environment in ("production", "staging"):
            raise ValueError(f"SECRET_KEY must be at least 32 characters (got {len(v)}).")

        return v

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:*",
        "http://127.0.0.1:*",
        "*",  # Allow all origins in development
    ]

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    # Worker
    WORKER_HEARTBEAT_TIMEOUT: int = 120
    MAX_WORKER_RETRIES: int = 3

    # Task Execution
    MAX_CONCURRENT_TASKS: int = 100
    TASK_EXECUTION_TIMEOUT: int = 600

    # Workflow Engine
    MAX_CONCURRENT_WORKFLOWS: int = 50
    WORKFLOW_NODE_TIMEOUT: int = 300

    # Task Allocator Weights
    ALLOCATOR_WEIGHT_TOOL_MATCH: float = 0.40
    ALLOCATOR_WEIGHT_RESOURCES: float = 0.30
    ALLOCATOR_WEIGHT_LOAD_BALANCE: float = 0.20
    ALLOCATOR_WEIGHT_AFFINITY: float = 0.10

    # Database Query
    DB_QUERY_TIMEOUT_SECONDS: int = 30

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_TTL_SECONDS: int = 3600

    # API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency injection for settings."""
    return settings
