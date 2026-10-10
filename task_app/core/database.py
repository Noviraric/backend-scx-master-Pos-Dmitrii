import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from task_app.core.config import get_settings

settings = get_settings()

# Для SQLite необходим параметр check_same_thread: False
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Генератор сессии БД (DI жизненный цикл: per-request).
    Сессия закрывается автоматически в блоке finally.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
