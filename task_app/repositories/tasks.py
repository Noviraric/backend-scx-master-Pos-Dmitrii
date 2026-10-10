from typing import List, Optional
from sqlalchemy.orm import Session
from task_app.models.tasks import Task
from task_app.schemas.tasks import CreateTaskRequest, UpdateTaskRequest

class TaskRepository:
    """Репозиторий для работы с сущностью Task в базе данных."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Task]:
        """Получить коллекцию всех задач с пагинацией."""
        return (
            self.db.query(Task)
            .order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_id(self, task_id: int) -> Optional[Task]:
        """Получить одну задачу по её ID."""
        return self.db.query(Task).filter(Task.id == task_id).first()

    def create(self, task_data: CreateTaskRequest) -> Task:
        """Создать новую задачу в БД."""
        db_task = Task(
            title=task_data.title.strip(),
            description=task_data.description.strip() if task_data.description else None,
            priority=task_data.priority,
            done=task_data.done,
        )
        self.db.add(db_task)
        self.db.commit()
        self.db.refresh(db_task)
        return db_task

    def update(self, task_id: int, task_data: UpdateTaskRequest) -> Optional[Task]:
        """Обновить существующую задачу по ID."""
        db_task = self.get_by_id(task_id)
        if not db_task:
            return None

        update_dict = task_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if key == "title" and value is not None:
                value = value.strip()
            elif key == "description" and value is not None:
                value = value.strip()
            setattr(db_task, key, value)

        self.db.commit()
        self.db.refresh(db_task)
        return db_task

    def delete(self, task_id: int) -> bool:
        """Удалить задачу по ID. Возвращает True, если удалена, иначе False."""
        db_task = self.get_by_id(task_id)
        if not db_task:
            return False

        self.db.delete(db_task)
        self.db.commit()
        return True

    def count(self) -> int:
        """Общее количество задач в БД."""
        return self.db.query(Task).count()
