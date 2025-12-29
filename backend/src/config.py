"""
Application Configuration

Environment variable management using Pydantic Settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables

    All settings can be overridden via .env file or environment variables.
    """

    # Application
    APP_NAME: str = "Multi-Agent on the Web"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

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
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ]

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds

    # Worker Agent
    WORKER_HEARTBEAT_TIMEOUT: int = 120  # seconds (2x heartbeat interval)
    MAX_WORKER_RETRIES: int = 3

    # Task Execution
    MAX_CONCURRENT_TASKS: int = 100
    TASK_EXECUTION_TIMEOUT: int = 600  # 10 minutes

    # Checkpoint
    EVALUATION_SCORE_THRESHOLD: float = 7.0  # Trigger checkpoint if score < 7.0

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG | INFO | WARNING | ERROR | CRITICAL
    LOG_FORMAT: str = "json"  # json | text

    # API Keys (for evaluation framework)
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
    """
    Dependency injection for settings

    Usage:
        @app.get("/config")
        def get_config(settings: Settings = Depends(get_settings)):
            return {"app_name": settings.APP_NAME}
    """
    return settings
