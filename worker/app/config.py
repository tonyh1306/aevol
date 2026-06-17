from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    BACKEND_URL: str = "http://localhost:8000"

    HIGH_QUEUE: str = "eval:queue:high"
    NORMAL_QUEUE: str = "eval:queue:normal"
    RETRY_QUEUE: str = "eval:queue:retry"
    DEAD_QUEUE: str = "eval:queue:dead"
    SSE_CHANNEL: str = "eval:sse:channel"

    TASK_LOCK_TTL: int = 60
    HEARTBEAT_INTERVAL: int = 10
    POLL_INTERVAL: float = 1.0

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    LOG_LEVEL: str = "INFO"
    WORKER_VERSION: str = "0.1.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
