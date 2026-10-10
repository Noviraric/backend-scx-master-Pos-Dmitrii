from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Task Tracker API"
    app_version: str = "1.0.0"
    debug: bool = True
    database_url: str = "sqlite:///./tasks.db"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    """Singleton-настройки приложения (рекомендация из лекции 7)."""
    return Settings()
