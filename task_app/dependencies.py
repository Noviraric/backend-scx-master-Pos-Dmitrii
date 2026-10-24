from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from task_app.core.database import get_db
from task_app.models.users import User
from task_app.repositories.tasks import TaskRepository
from task_app.repositories.users import UserRepository
from task_app.services.tasks import TaskService
from task_app.services.auth import AuthService, AuthenticationError
from task_app.services.notification_service import NotificationService

# Swagger возьмёт отсюда адрес логина для кнопки Authorize
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")

def get_notification_service() -> NotificationService:
    """Провайдер сервиса уведомлений (Singleton)."""
    return NotificationService()

def get_task_repository(db: Session = Depends(get_db)) -> TaskRepository:
    """Провайдер репозитория задач с внедрением сессии БД (per-request)."""
    return TaskRepository(db)

def get_task_service(
    repo: TaskRepository = Depends(get_task_repository),
    notifier: NotificationService = Depends(get_notification_service),
) -> TaskService:
    """
    Провайдер сервиса задач (цепочка: Route -> Service -> Repository -> Session).
    Вся композиция собирается фреймворком через Depends.
    """
    return TaskService(repo=repo, notifier=notifier)

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Провайдер репозитория пользователей (per-request)."""
    return UserRepository(db)

def get_auth_service(repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    """Провайдер сервиса аутентификации."""
    return AuthService(repo)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """
    Аутентификация: единая точка проверки токена.
    Без заголовка Authorization oauth2_scheme сам вернёт 401.
    """
    try:
        return service.get_user_by_token(token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_admin(user: User = Depends(get_current_user)) -> User:
    """Авторизация: пропускает дальше только пользователей с ролью admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав: требуется роль admin",
        )
    return user
