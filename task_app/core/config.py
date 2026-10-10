from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Task Tracker API"
    app_version: str = "1.0.0"
    debug: bool = True
    database_url: str = "sqlite:///./tasks.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()