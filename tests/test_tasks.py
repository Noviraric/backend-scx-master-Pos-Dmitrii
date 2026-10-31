from unittest.mock import AsyncMock, Mock, create_autospec
import pytest
from task_app.adapters.file_storage import FileStorage, FileStorageError, StoredFileNotFound
from task_app.core.exceptions import (
    AvatarNotFoundException,
    AvatarNotSetException,
    ErrorCode,
    FileTooLargeException,
    InvalidFileException,
    TaskLimitExceededException,
    TaskNotFoundException,
    TaskTitleTooShortException,
)
from task_app.models.tasks import Task
from task_app.schemas.tasks import CreateTaskRequest
from task_app.services.tasks import MAX_AVATAR_SIZE, TaskService, detect_image_type

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG = b"\xff\xd8\xff" + b"\x00" * 100


def make_repo(**kwargs) -> AsyncMock:
    """Мок асинхронного репозитория: все методы — корутины."""
    repo = AsyncMock()
    for name, value in kwargs.items():
        getattr(repo, name).return_value = value
    return repo


async def test_create_task_with_mock_repo():
    """
    Тест сервиса с моком репозитория (по слайду 9 лекции 7).
    База данных не запускается — тест быстрый, проверяет вызовы и возвращаемое значение.
    """
    mock_repo = make_repo(
        count=0,
        create=Task(id=1, title="Купить молоко", description="2 пакета", priority=2, done=False),
    )
    mock_notifier = Mock()

    service = TaskService(repo=mock_repo, notifier=mock_notifier)
    data = CreateTaskRequest(title="Купить молоко", description="2 пакета", priority=2)

    result = await service.create_task(data)

    mock_repo.create.assert_awaited_once()
    mock_notifier.notify.assert_called_once()
    assert result.id == 1
    assert result.title == "Купить молоко"


async def test_create_task_validation_empty_title():
    """3 пробела проходят Pydantic (min_length=3), но отсекаются сервисом после strip()."""
    service = TaskService(repo=make_repo(count=0))

    data = CreateTaskRequest(title="   ", priority=1)
    with pytest.raises(TaskTitleTooShortException) as exc_info:
        await service.create_task(data)
    assert exc_info.value.detail["code"] == ErrorCode.TASK_TITLE_TOO_SHORT
    assert exc_info.value.detail["field"] == "title"


async def test_task_limit_exceeded():
    """Проверка бизнес-правила лимита в 100 задач (слайд 8 лекции 7А)."""
    service = TaskService(repo=make_repo(count=100))

    data = CreateTaskRequest(title="Новая задача", priority=1)
    with pytest.raises(TaskLimitExceededException):
        await service.create_task(data)


async def test_get_task_not_found():
    """Несуществующая задача — TaskNotFoundException с id в details."""
    service = TaskService(repo=make_repo(get_by_id=None))

    with pytest.raises(TaskNotFoundException) as exc_info:
        await service.get_task_by_id(999)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["details"] == {"task_id": 999}


# --- Аватарка: сервис с моком FileStorage (слайд 34 пары 21А) ---

def test_detect_image_type():
    assert detect_image_type(PNG) == ("image/png", "png")
    assert detect_image_type(JPEG) == ("image/jpeg", "jpg")
    assert detect_image_type(b"GIF89a...") == ("image/gif", "gif")
    assert detect_image_type(b"MZ\x90\x00 executable") is None


async def test_upload_avatar_saves_key_and_calls_storage():
    storage = create_autospec(FileStorage, instance=True)
    storage.upload.return_value = "tasks/1/avatar.png"
    task = Task(id=1, title="Задача", avatar_key=None)
    repo = make_repo(get_by_id=task)
    service = TaskService(repo=repo, storage=storage)

    key = await service.upload_task_avatar(task_id=1, file_data=PNG, filename="me.png")

    assert key == "tasks/1/avatar.png"
    storage.upload.assert_called_once_with(
        "tasks/1/avatar.png", PNG, "image/png",
        metadata={"task-id": "1", "original-filename": "me.png"},
    )
    repo.update_avatar_key.assert_awaited_once_with(task, "tasks/1/avatar.png")


async def test_upload_avatar_replaces_old_key_and_deletes_old_object():
    storage = create_autospec(FileStorage, instance=True)
    task = Task(id=1, title="Задача", avatar_key="tasks/1/avatar.jpg")
    service = TaskService(repo=make_repo(get_by_id=task), storage=storage)

    await service.upload_task_avatar(1, PNG, "new.png")

    storage.delete.assert_called_once_with("tasks/1/avatar.jpg")


async def test_upload_avatar_old_object_delete_error_is_not_fatal():
    storage = create_autospec(FileStorage, instance=True)
    storage.delete.side_effect = FileStorageError("boom")
    task = Task(id=1, title="Задача", avatar_key="tasks/1/avatar.jpg")
    service = TaskService(repo=make_repo(get_by_id=task), storage=storage)

    assert await service.upload_task_avatar(1, PNG, "new.png") == "tasks/1/avatar.png"


@pytest.mark.parametrize("data, exc", [
    (b"", InvalidFileException),
    (b"just text renamed to .png", InvalidFileException),
    (PNG + b"\x00" * MAX_AVATAR_SIZE, FileTooLargeException),
], ids=["empty", "not-an-image", "too-large"])
async def test_upload_avatar_rejects_bad_files(data, exc):
    storage = create_autospec(FileStorage, instance=True)
    service = TaskService(repo=make_repo(get_by_id=Task(id=1, title="Задача")), storage=storage)

    with pytest.raises(exc):
        await service.upload_task_avatar(1, data, "x.png")
    storage.upload.assert_not_called()


async def test_upload_avatar_task_not_found():
    storage = create_autospec(FileStorage, instance=True)
    service = TaskService(repo=make_repo(get_by_id=None), storage=storage)

    with pytest.raises(TaskNotFoundException):
        await service.upload_task_avatar(999, PNG, "x.png")
    storage.upload.assert_not_called()


async def test_get_avatar_url_errors():
    storage = create_autospec(FileStorage, instance=True)
    service = TaskService(repo=make_repo(get_by_id=Task(id=1, title="Задача", avatar_key=None)), storage=storage)
    with pytest.raises(AvatarNotSetException):
        await service.get_task_avatar_url(1)

    storage.get_download_url.side_effect = StoredFileNotFound("tasks/1/avatar.png")
    service = TaskService(repo=make_repo(get_by_id=Task(id=1, title="Задача", avatar_key="tasks/1/avatar.png")), storage=storage)
    with pytest.raises(AvatarNotFoundException):
        await service.get_task_avatar_url(1)


async def test_delete_avatar_clears_key():
    """Домашнее задание пары 21Б: DELETE /tasks/{id}/avatar."""
    storage = create_autospec(FileStorage, instance=True)
    task = Task(id=1, title="Задача", avatar_key="tasks/1/avatar.png")
    repo = make_repo(get_by_id=task)
    service = TaskService(repo=repo, storage=storage)

    await service.delete_task_avatar(1)

    storage.delete.assert_called_once_with("tasks/1/avatar.png")
    repo.update_avatar_key.assert_awaited_once_with(task, None)
