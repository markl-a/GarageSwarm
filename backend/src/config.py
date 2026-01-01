"""
Application Configuration

Environment variable management using Pydantic Settings.
Includes security validations for production environments.
"""

import secrets
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables

    All settings can be overridden via .env file or environment variables.

    Security:
        - SECRET_KEY must be set via environment variable in production
        - SECRET_KEY must be at least 32 characters for security
        - Default SECRET_KEY is only allowed in development mode
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
    # In production, SECRET_KEY MUST be set via environment variable
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Validate SECRET_KEY security requirements.

        In development: generates a random key if not provided (with warning)
        In production: requires a strong key from environment variable
        """
        # This will be called before the object is fully initialized
        # so we can't access self.ENVIRONMENT directly
        import os
        environment = os.getenv("ENVIRONMENT", "development").lower()

        # If no key provided
        if not v:
            if environment in ("production", "staging"):
                raise ValueError(
                    "SECRET_KEY environment variable is required in production/staging. "
                    "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            # Development: generate a random key (will change on restart)
            import warnings
            warnings.warn(
                "SECRET_KEY not set - using random key. "
                "Sessions will be invalidated on restart. "
                "Set SECRET_KEY environment variable for persistence.",
                UserWarning
            )
            return secrets.token_urlsafe(32)

        # Check if it's the old insecure default
        insecure_defaults = [
            "your-secret-key-change-in-production",
            "secret",
            "password",
            "changeme",
        ]
        if v.lower() in insecure_defaults:
            if environment in ("production", "staging"):
                raise ValueError(
                    f"Insecure SECRET_KEY detected. "
                    f"Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )

        # Check minimum length (32 characters for 256-bit security)
        if len(v) < 32:
            if environment in ("production", "staging"):
                raise ValueError(
                    f"SECRET_KEY must be at least 32 characters (got {len(v)}). "
                    f"Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            import warnings
            warnings.warn(
                f"SECRET_KEY is shorter than recommended 32 characters ({len(v)} chars). "
                "Consider using a longer key for better security.",
                UserWarning
            )

        return v

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds

    # Worker Agent
    WORKER_HEARTBEAT_TIMEOUT: int = 120  # seconds (2x heartbeat interval)
    MAX_WORKER_RETRIES: int = 3

    # Task Execution
    MAX_CONCURRENT_TASKS: int = 100
    TASK_EXECUTION_TIMEOUT: int = 600  # 10 minutes

    # Task Scheduler
    MAX_CONCURRENT_SUBTASKS: int = 20  # System-wide limit for parallel subtasks
    MAX_SUBTASKS_PER_WORKER: int = 1   # Per-worker subtask limit
    SCHEDULER_INTERVAL_SECONDS: int = 30  # Scheduling loop interval

    # Task Allocator
    MAX_QUEUE_ALLOCATION_ATTEMPTS: int = 100  # Safety limit for queue reallocation loop
    ALLOCATION_BATCH_SIZE: int = 50  # Max subtasks to allocate per batch

    # Task Allocator Weights (must sum to 1.0)
    ALLOCATOR_WEIGHT_TOOL_MATCH: float = 0.50  # Weight for tool matching score
    ALLOCATOR_WEIGHT_RESOURCES: float = 0.30   # Weight for resource availability
    ALLOCATOR_WEIGHT_PRIVACY: float = 0.20     # Weight for privacy compatibility

    # Resource Thresholds (percentage)
    RESOURCE_THRESHOLD_CPU_HIGH: int = 80      # High CPU usage threshold
    RESOURCE_THRESHOLD_MEMORY_HIGH: int = 85   # High memory usage threshold
    RESOURCE_THRESHOLD_DISK_HIGH: int = 90     # High disk usage threshold

    # Database Query
    DB_QUERY_TIMEOUT_SECONDS: int = 30  # Timeout for database queries

    # Review Service
    REVIEW_SCORE_THRESHOLD: float = 6.0  # Scores below this trigger auto-fix
    MAX_REVIEW_FIX_CYCLES: int = 2  # Max review-fix cycles before escalation

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100  # Max requests per window
    RATE_LIMIT_WINDOW: int = 60  # Window size in seconds

    # Checkpoint Auto-Trigger Configuration
    EVALUATION_SCORE_THRESHOLD: float = 7.0  # Trigger checkpoint if score < 7.0
    CHECKPOINT_SUBTASK_INTERVAL: int = 5  # Trigger after N subtasks complete
    CHECKPOINT_MAX_CORRECTION_CYCLES: int = 3  # Max correction cycles before escalation
    CHECKPOINT_TIMEOUT_HOURS: int = 24  # Hours before timeout escalation
    CHECKPOINT_ENABLE_ERROR_TRIGGER: bool = True  # Auto-trigger on errors
    CHECKPOINT_ENABLE_EVALUATION_TRIGGER: bool = True  # Auto-trigger on low scores
    CHECKPOINT_ENABLE_PERIODIC_TRIGGER: bool = True  # Auto-trigger periodically
    CHECKPOINT_ENABLE_TIMEOUT_TRIGGER: bool = True  # Auto-trigger on timeout

    # Pool Monitor
    POOL_MONITOR_INTERVAL: int = 30  # Check interval in seconds
    POOL_UTILIZATION_WARNING: float = 70.0    # Warning at 70% utilization
    POOL_UTILIZATION_CRITICAL: float = 90.0   # Critical at 90% utilization
    POOL_BACKPRESSURE_THRESHOLD: float = 85.0 # Start rejecting at 85%
    POOL_BACKPRESSURE_COOLDOWN: float = 5.0   # Cooldown seconds

    # Worker Health Check
    WORKER_HEALTH_CHECK_INTERVAL: int = 30    # Check interval in seconds

    # Dynamic Timeout Multipliers (based on subtask complexity 1-5)
    TIMEOUT_MULTIPLIER_COMPLEXITY_1: float = 1.0   # Simple tasks
    TIMEOUT_MULTIPLIER_COMPLEXITY_2: float = 1.5   # Basic tasks
    TIMEOUT_MULTIPLIER_COMPLEXITY_3: float = 2.0   # Medium complexity
    TIMEOUT_MULTIPLIER_COMPLEXITY_4: float = 3.0   # High complexity
    TIMEOUT_MULTIPLIER_COMPLEXITY_5: float = 4.0   # Very high complexity

    # Evaluation Thresholds
    EVAL_CODE_QUALITY_WEIGHT: float = 0.25    # Code quality weight
    EVAL_COMPLETENESS_WEIGHT: float = 0.30    # Completeness weight
    EVAL_SECURITY_WEIGHT: float = 0.25        # Security weight
    EVAL_ARCHITECTURE_WEIGHT: float = 0.20    # Architecture weight
    EVAL_GRADE_EXCELLENT: float = 9.0         # Excellent threshold
    EVAL_GRADE_GOOD: float = 7.0              # Good threshold
    EVAL_GRADE_ACCEPTABLE: float = 5.0        # Acceptable threshold
    EVAL_GRADE_POOR: float = 3.0              # Poor threshold

    # Code Quality Evaluator
    CODE_QUALITY_MAX_LINE_LENGTH: int = 120       # Max line length
    CODE_QUALITY_MAX_COMPLEXITY: int = 10         # Max cyclomatic complexity
    CODE_QUALITY_MAX_BLANK_LINES: int = 2         # Max consecutive blank lines

    # Architecture Evaluator
    ARCH_GOD_CLASS_THRESHOLD: int = 20            # Max methods in a class
    ARCH_LONG_METHOD_THRESHOLD: int = 50          # Max lines in a method
    ARCH_MAX_PARAMETERS: int = 5                  # Max function parameters
    ARCH_MAX_NESTING_DEPTH: int = 4               # Max nesting depth
    ARCH_LARGE_FILE_THRESHOLD: int = 500          # Max lines in a file

    # Security Evaluator
    SECURITY_HUMAN_REVIEW_THRESHOLD: float = 4.0  # Trigger review below this score

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG | INFO | WARNING | ERROR | CRITICAL
    LOG_FORMAT: str = "json"  # json | text
    LOG_TTL_SECONDS: int = 3600  # Redis log TTL (1 hour)

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
