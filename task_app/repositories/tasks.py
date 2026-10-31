from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from task_app.models.tasks import Task
from task_app.schemas.tasks import CreateTaskRequest, UpdateTaskRequest

class TaskRepository:
    """
    Репозиторий для работы с сущностью Task в базе данных.
    Единственное место с I/O к БД: каждый запрос — через await.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Task]:
        """Получить коллекцию всех задач с пагинацией."""
        result = await self.db.execute(
            select(Task)
            .order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, task_id: int) -> Optional[Task]:
        """Получить одну задачу по её ID."""
        return await self.db.get(Task, task_id)

    async def create(self, task_data: CreateTaskRequest) -> Task:
        """Создать новую задачу в БД."""
        db_task = Task(
            title=task_data.title.strip(),
            description=task_data.description.strip() if task_data.description else None,
            priority=task_data.priority,
            done=task_data.done,
        )
        self.db.add(db_task)              # только запоминает объект — не I/O, без await
        await self.db.commit()            # отправка в БД
        await self.db.refresh(db_task)    # перечитать из БД
        return db_task

    async def update(self, db_task: Task, task_data: UpdateTaskRequest) -> Task:
        """Обновить переданные поля существующей задачи."""
        update_dict = task_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if key in ("title", "description") and value is not None:
                value = value.strip()
            setattr(db_task, key, value)

        await self.db.commit()
        await self.db.refresh(db_task)
        return db_task

    async def update_avatar_key(self, db_task: Task, key: Optional[str]) -> None:
        """Сохранить ключ аватарки в S3 (None — аватарки нет)."""
        db_task.avatar_key = key
        await self.db.commit()

    async def delete(self, db_task: Task) -> None:
        """Удалить задачу."""
        await self.db.delete(db_task)
        await self.db.commit()

    async def count(self) -> int:
        """Общее количество задач в БД."""
        return await self.db.scalar(select(func.count()).select_from(Task))
