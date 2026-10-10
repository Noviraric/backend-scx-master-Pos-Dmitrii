from fastapi import Depends
from sqlalchemy.orm import Session
from task_app.core.database import get_db
from task_app.repositories.tasks import TaskRepository
from task_app.services.tasks import TaskService
from task_app.services.notification_service import NotificationService

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
