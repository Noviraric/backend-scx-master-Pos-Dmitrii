import asyncio
import logging
from typing import List, Optional
from task_app.adapters.file_storage import FileStorage, FileStorageError, StoredFileNotFound
from task_app.core.exceptions import (
    AvatarNotFoundException,
    AvatarNotSetException,
    FileTooLargeException,
    InvalidFileException,
    InvalidPaginationException,
    TaskLimitExceededException,
    TaskNotFoundException,
    TaskTitleTooShortException,
)
from task_app.models.tasks import Task
from task_app.repositories.tasks import TaskRepository
from task_app.schemas.tasks import CreateTaskRequest, UpdateTaskRequest
from task_app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

MIN_TITLE_LENGTH = 3
MAX_TASKS = 100  # бизнес-лимит на число задач в системе (из лекции 7А)
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 МБ
AVATAR_URL_EXPIRES = 3600  # срок жизни подписанной ссылки, секунды

_IMAGE_SIGNATURES = [  # сигнатура, MIME-тип, расширение
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"GIF87a", "image/gif", "gif"),
    (b"GIF89a", "image/gif", "gif"),
]


def detect_image_type(data: bytes) -> Optional[tuple[str, str]]:
    """Тип файла по первым байтам (магическим числам), а не по Content-Type от клиента."""
    for signature, content_type, extension in _IMAGE_SIGNATURES:
        if data.startswith(signature):
            return content_type, extension
    return None


class TaskService:
    """
    Бизнес-логика для задач.
    Ошибки — исключения из core/exceptions.py: сервис их только бросает,
    формат ответа решает глобальный обработчик.
    Хранилище — через интерфейс FileStorage; boto3 синхронный, поэтому вызовы
    уходят в поток (asyncio.to_thread), чтобы не останавливать цикл событий.
    """

    def __init__(
        self,
        repo: TaskRepository,
        storage: Optional[FileStorage] = None,
        notifier: Optional[NotificationService] = None,
    ):
        self.repo = repo
        self.storage = storage
        self.notifier = notifier or NotificationService()

    async def get_all_tasks(self, skip: int = 0, limit: int = 100) -> List[Task]:
        """Получить список всех задач с пагинацией."""
        if skip < 0:
            raise InvalidPaginationException("skip", "Параметр skip не может быть отрицательным")
        if limit <= 0 or limit > 500:
            raise InvalidPaginationException("limit", "Параметр limit должен быть в диапазоне от 1 до 500")
        return await self.repo.get_all(skip=skip, limit=limit)

    async def get_task_by_id(self, task_id: int) -> Task:
        """Получить одну задачу по ID. Если не найдена — TaskNotFoundException (404)."""
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundException(task_id)
        return task

    async def create_task(self, data: CreateTaskRequest) -> Task:
        """Создать задачу с проверкой бизнес-правил."""
        cleaned_title = data.title.strip() if data.title else ""
        if len(cleaned_title) < MIN_TITLE_LENGTH:
            raise TaskTitleTooShortException(min_length=MIN_TITLE_LENGTH)

        if await self.repo.count() >= MAX_TASKS:
            raise TaskLimitExceededException(limit=MAX_TASKS)

        data.title = cleaned_title
        task = await self.repo.create(data)

        # Вызов уведомления через композицию сервисов
        if self.notifier:
            self.notifier.notify(f"Создана новая задача #{task.id}: {task.title}")

        return task

    async def update_task(self, task_id: int, data: UpdateTaskRequest) -> Task:
        """Обновить существующую задачу."""
        task = await self.get_task_by_id(task_id)

        if data.title is not None:
            cleaned_title = data.title.strip()
            if len(cleaned_title) < MIN_TITLE_LENGTH:
                raise TaskTitleTooShortException(min_length=MIN_TITLE_LENGTH)
            data.title = cleaned_title

        updated_task = await self.repo.update(task, data)

        if self.notifier:
            self.notifier.notify(f"Задача #{task_id} обновлена: {updated_task.title} (done={updated_task.done})")

        return updated_task

    async def delete_task(self, task_id: int) -> None:
        """Удалить задачу по ID вместе с её аватаркой."""
        task = await self.get_task_by_id(task_id)
        avatar_key = task.avatar_key

        await self.repo.delete(task)
        if avatar_key:
            await self._delete_from_storage_quietly(avatar_key)

        if self.notifier:
            self.notifier.notify(f"Задача #{task_id} успешно удалена")

    # --- Аватарка задачи (S3) ---

    async def upload_task_avatar(self, task_id: int, file_data: bytes, filename: str) -> str:
        """Проверить файл, сохранить в хранилище и записать ключ в БД. Возвращает ключ."""
        task = await self.get_task_by_id(task_id)

        if not file_data:
            raise InvalidFileException("Файл пуст")
        if len(file_data) > MAX_AVATAR_SIZE:
            raise FileTooLargeException(max_bytes=MAX_AVATAR_SIZE)
        detected = detect_image_type(file_data)
        if detected is None:
            raise InvalidFileException(
                "Допустимы только PNG, JPEG и GIF",
                details={"allowed": ["image/png", "image/jpeg", "image/gif"]},
            )
        content_type, extension = detected

        key = f"tasks/{task_id}/avatar.{extension}"  # ключ строит сервер, расширение — из типа, не из имени
        old_key = task.avatar_key
        await asyncio.to_thread(
            self.storage.upload, key, file_data, content_type,
            metadata={"task-id": str(task_id), "original-filename": filename},
        )
        await self.repo.update_avatar_key(task, key)  # сначала хранилище, потом БД

        if old_key and old_key != key:
            await self._delete_from_storage_quietly(old_key)
        return key

    async def get_task_avatar_url(self, task_id: int) -> str:
        """Новая подписанная ссылка на аватарку при каждом вызове."""
        task = await self.get_task_by_id(task_id)
        if not task.avatar_key:
            raise AvatarNotSetException(task_id)
        try:
            return await asyncio.to_thread(self.storage.get_download_url, task.avatar_key, AVATAR_URL_EXPIRES)
        except StoredFileNotFound:
            raise AvatarNotFoundException(task_id, task.avatar_key)

    async def delete_task_avatar(self, task_id: int) -> None:
        """Удалить аватарку из хранилища и очистить avatar_key."""
        task = await self.get_task_by_id(task_id)
        if not task.avatar_key:
            raise AvatarNotSetException(task_id)
        await asyncio.to_thread(self.storage.delete, task.avatar_key)
        await self.repo.update_avatar_key(task, None)

    async def _delete_from_storage_quietly(self, key: str) -> None:
        """Удаление «хвоста» в хранилище: ошибку пишем в лог, но запрос не валим."""
        try:
            await asyncio.to_thread(self.storage.delete, key)
        except FileStorageError:
            logger.warning("Не удалось удалить объект %s из хранилища", key, exc_info=True)
