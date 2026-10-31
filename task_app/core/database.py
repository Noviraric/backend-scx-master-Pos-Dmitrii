from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from task_app.core.config import get_settings

settings = get_settings()

# Асинхронный движок: драйвер указывается в URL после «+» — asyncpg для PostgreSQL, aiosqlite для SQLite
engine = create_async_engine(settings.database_url, echo=settings.debug)

# expire_on_commit=False: после commit объекты остаются читаемыми без нового похода в БД
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()

async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Сессия БД на один запрос (DI жизненный цикл: per-request).
    async with закроет её, когда ответ будет отправлен.
    Одну AsyncSession нельзя использовать из нескольких корутин одновременно.
    """
    async with SessionLocal() as session:
        yield session
