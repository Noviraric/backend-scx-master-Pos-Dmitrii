from functools import lru_cache
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from task_app.adapters.file_storage import FileStorage
from task_app.adapters.s3_client import create_s3_client
from task_app.adapters.s3_storage import S3Storage
from task_app.core.config import get_settings
from task_app.core.database import get_db
from task_app.core.exceptions import PermissionDeniedException
from task_app.models.users import User
from task_app.repositories.tasks import TaskRepository
from task_app.repositories.users import UserRepository
from task_app.services.tasks import TaskService
from task_app.services.auth import AuthService
from task_app.services.notification_service import NotificationService

# Swagger возьмёт отсюда адрес логина для кнопки Authorize
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")

# Провайдеры ничего не ждут и не блокируют, поэтому async def:
# FastAPI выполнит их прямо в цикле событий, без похода в пул потоков.

async def get_notification_service() -> NotificationService:
    """Провайдер сервиса уведомлений (Singleton)."""
    return NotificationService()

@lru_cache
def get_file_storage() -> FileStorage:
    """
    Один клиент хранилища на процесс: @lru_cache запоминает результат первого вызова.
    Клиент boto3 дорого создавать, и он потокобезопасен.
    """
    return S3Storage(create_s3_client(), get_settings().s3_bucket)

async def get_task_repository(db: AsyncSession = Depends(get_db)) -> TaskRepository:
    """Провайдер репозитория задач с внедрением сессии БД (per-request)."""
    return TaskRepository(db)

async def get_task_service(
    repo: TaskRepository = Depends(get_task_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: NotificationService = Depends(get_notification_service),
) -> TaskService:
    """
    Провайдер сервиса задач (цепочка: Route -> Service -> Repository -> Session).
    Вся композиция собирается фреймворком через Depends.
    """
    return TaskService(repo=repo, storage=storage, notifier=notifier)

async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Провайдер репозитория пользователей (per-request)."""
    return UserRepository(db)

async def get_auth_service(repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    """Провайдер сервиса аутентификации."""
    return AuthService(repo)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """
    Аутентификация: единая точка проверки токена.
    Без заголовка Authorization oauth2_scheme сам вернёт 401, невалидный токен — InvalidTokenException.
    """
    return await service.get_user_by_token(token)

async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Авторизация: пропускает дальше только пользователей с ролью admin."""
    if user.role != "admin":
        raise PermissionDeniedException(required_role="admin")
    return user
