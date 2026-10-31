from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class TaskBase(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=100,
        description="Название задачи (от 3 до 100 символов)",
        examples=["Подготовить отчёт по проекту"]
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Подробное описание задачи",
        examples=["Составить презентацию и сверить метрики"]
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Приоритет от 1 (низкий) до 5 (критический)",
        examples=[3]
    )
    done: bool = Field(
        default=False,
        description="Статус выполнения задачи",
        examples=[False]
    )

class CreateTaskRequest(TaskBase):
    """Модель для создания задачи (POST /tasks). id и created_at назначаются сервером."""
    pass

# Алиас для совместимости
TaskCreate = CreateTaskRequest

class UpdateTaskRequest(BaseModel):
    """Модель для обновления задачи (PUT/PATCH /tasks/{id}). Все поля опциональны."""
    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Новое название задачи",
        examples=["Обновлённое название"]
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Новое описание задачи"
    )
    priority: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Новый приоритет (1-5)"
    )
    done: Optional[bool] = Field(
        default=None,
        description="Новый статус выполнения"
    )

# Алиас для совместимости
TaskUpdate = UpdateTaskRequest

class TaskResponse(TaskBase):
    """Модель ответа клиенту (GET /tasks, GET /tasks/{id}, POST, PUT)."""
    id: int = Field(description="Уникальный идентификатор задачи", examples=[1])
    created_at: datetime = Field(description="Дата и время создания")
    updated_at: datetime = Field(description="Дата и время последнего обновления")
    avatar_key: Optional[str] = Field(default=None, description="Ключ аватарки в S3 (ссылка — через GET /tasks/{id}/avatar)")

    model_config = ConfigDict(from_attributes=True)

class AvatarResponse(BaseModel):
    """Ответ на загрузку / запрос аватарки: ключ постоянный, url — временный подписанный."""
    task_id: int
    key: str = Field(examples=["tasks/1/avatar.png"])
    url: str = Field(description="Подписанная ссылка на скачивание, действует 1 час")
