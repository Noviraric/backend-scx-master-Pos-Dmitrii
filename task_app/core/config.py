from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Синхронные драйверы из старых .env → асинхронные аналоги
_ASYNC_DRIVERS = {
    "postgresql://": "postgresql+asyncpg://",
    "postgresql+psycopg2://": "postgresql+asyncpg://",
    "sqlite:///": "sqlite+aiosqlite:///",
}

class Settings(BaseSettings):
    app_name: str = "Task Tracker API"
    app_version: str = "1.0.0"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./tasks.db"

    # JWT: секрет задаётся в .env, значение по умолчанию — только для локальной разработки
    secret_key: str = "change-me-please"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # S3: ключи обязательны — без них приложение не стартует и называет переменную (fail fast)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "task-avatars"
    s3_region: str = "us-east-1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def use_async_driver(cls, url: str) -> str:
        """Движок асинхронный, поэтому URL должен указывать async-драйвер (asyncpg / aiosqlite)."""
        for sync_prefix, async_prefix in _ASYNC_DRIVERS.items():
            if url.startswith(sync_prefix):
                return async_prefix + url[len(sync_prefix):]
        return url

@lru_cache
def get_settings() -> Settings:
    return Settings()
