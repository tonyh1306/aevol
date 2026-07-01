from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    BACKEND_URL: str = "http://localhost:8000"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"
    POLL_INTERVAL: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
