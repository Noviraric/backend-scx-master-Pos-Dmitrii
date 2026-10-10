# Reference database configuration
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Book App"
    database_url: str = "sqlite:///./db.sqlite"

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
