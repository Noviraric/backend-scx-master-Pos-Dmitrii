import os

# S3-ключи в настройках обязательны. Тесты к хранилищу не ходят — подставляем заглушки,
# если их нет в окружении (до импорта приложения, иначе Settings() упадёт).
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")

from typing import Optional
import httpx
import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from task_app.adapters.file_storage import FileStorage, StoredFileNotFound
from task_app.core.database import Base, get_db
from task_app.dependencies import get_file_storage
from task_app.main import app
from task_app.models.users import User


class InMemoryStorage(FileStorage):
    """Хранилище-словарь вместо S3: тестам не нужен живой сервер."""

    def __init__(self):
        self.objects: dict[str, dict] = {}

    def upload(self, key: str, data: bytes, content_type: str,
               metadata: Optional[dict[str, str]] = None) -> str:
        self.objects[key] = {"data": data, "content_type": content_type, "metadata": metadata or {}}
        return key

    def get_download_url(self, key: str, expires_in: int = 3600) -> str:
        if key not in self.objects:
            raise StoredFileNotFound(key)
        return f"https://storage.test/task-avatars/{key}?X-Amz-Expires={expires_in}"

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


@pytest.fixture
async def session_factory():
    # Отдельная БД в памяти: тесты не трогают рабочую базу
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
async def client(session_factory, storage):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_file_storage] = lambda: storage
    # raise_app_exceptions=False: необработанная ошибка превращается в ответ 500, как на настоящем сервере
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


ALICE = {"username": "alice", "email": "alice@example.com", "password": "secret123"}


async def register_and_login(client: httpx.AsyncClient, user: dict = ALICE) -> dict:
    await client.post("/v1/auth/register", json=user)
    resp = await client.post("/v1/auth/login", data={"username": user["username"], "password": user["password"]})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def make_admin(session_factory):
    async def _make_admin(username: str) -> None:
        async with session_factory() as session:
            await session.execute(update(User).where(User.username == username).values(role="admin"))
            await session.commit()
    return _make_admin


@pytest.fixture
async def auth_headers(client) -> dict:
    return await register_and_login(client)
