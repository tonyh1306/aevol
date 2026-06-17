from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://eval:changeme@localhost/evaldb"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 20

    # Queue names
    HIGH_QUEUE: str = "eval:queue:high"
    NORMAL_QUEUE: str = "eval:queue:normal"
    RETRY_QUEUE: str = "eval:queue:retry"
    DEAD_QUEUE: str = "eval:queue:dead"
    SSE_CHANNEL: str = "eval:sse:channel"

    # Worker health
    TASK_LOCK_TTL: int = 60
    HEARTBEAT_INTERVAL: int = 10
    WORKER_DEAD_THRESHOLD: int = 30

    # Storage
    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 100

    # Security
    SECRET_KEY: str = "changeme_in_production"

    # Observability
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""

    # Regression detection thresholds (relative delta %)
    REGRESSION_THRESHOLD_PCT: float = 5.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
