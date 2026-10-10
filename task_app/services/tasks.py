from typing import List, Optional
from task_app.repositories.tasks import TaskRepository
from task_app.schemas.tasks import CreateTaskRequest, UpdateTaskRequest
from task_app.models.tasks import Task
from task_app.services.notification_service import NotificationService

class TaskService:
    """
    Бизнес-логика для задач.
    Чистый Python: ни одного импорта FastAPI!
    Ошибки валидации и бизнес-правил выбрасываются как ValueError.
    """

    def __init__(self, repo: TaskRepository, notifier: Optional[NotificationService] = None):
        self.repo = repo
        self.notifier = notifier or NotificationService()

    def get_all_tasks(self, skip: int = 0, limit: int = 100) -> List[Task]:
        """Получить список всех задач с пагинацией."""
        if skip < 0:
            raise ValueError("Параметр skip не может быть отрицательным")
        if limit <= 0 or limit > 500:
            raise ValueError("Параметр limit должен быть в диапазоне от 1 до 500")
        return self.repo.get_all(skip=skip, limit=limit)

    def get_task_by_id(self, task_id: int) -> Task:
        """Получить одну задачу по ID. Если не найдена — ValueError."""
        if task_id <= 0:
            raise ValueError("ID задачи должен быть положительным числом")
        task = self.repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Задача с id={task_id} не найдена")
        return task

    def create_task(self, data: CreateTaskRequest) -> Task:
        """Создать задачу с проверкой бизнес-правил."""
        cleaned_title = data.title.strip() if data.title else ""
        if len(cleaned_title) < 3:
            raise ValueError("Длина названия задачи должна быть не менее 3 символов")
        if len(cleaned_title) > 100:
            raise ValueError("Длина названия задачи не может превышать 100 символов")

        # Бизнес-лимит на максимальное число задач в системе (из лекции 7А)
        if self.repo.count() >= 100:
            raise ValueError("Достигнут системный лимит в 100 задач")

        # Приводим к очищенным данным
        data.title = cleaned_title
        task = self.repo.create(data)

        # Вызов уведомления через композицию сервисов
        if self.notifier:
            self.notifier.notify(f"Создана новая задача #{task.id}: {task.title}")

        return task

    def update_task(self, task_id: int, data: UpdateTaskRequest) -> Task:
        """Обновить существующую задачу."""
        if task_id <= 0:
            raise ValueError("ID задачи должен быть положительным числом")

        # Проверяем, существует ли задача
        existing = self.repo.get_by_id(task_id)
        if not existing:
            raise ValueError(f"Задача с id={task_id} не найдена")

        if data.title is not None:
            cleaned_title = data.title.strip()
            if len(cleaned_title) < 3:
                raise ValueError("Длина названия задачи должна быть не менее 3 символов")
            data.title = cleaned_title

        updated_task = self.repo.update(task_id, data)
        if not updated_task:
            raise ValueError(f"Не удалось обновить задачу с id={task_id}")

        if self.notifier:
            self.notifier.notify(f"Задача #{task_id} обновлена: {updated_task.title} (done={updated_task.done})")

        return updated_task

    def delete_task(self, task_id: int) -> None:
        """Удалить задачу по ID."""
        if task_id <= 0:
            raise ValueError("ID задачи должен быть положительным числом")

        task = self.repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Задача с id={task_id} не найдена")

        deleted = self.repo.delete(task_id)
        if not deleted:
            raise ValueError(f"Не удалось удалить задачу с id={task_id}")

        if self.notifier:
            self.notifier.notify(f"Задача #{task_id} успешно удалена")
