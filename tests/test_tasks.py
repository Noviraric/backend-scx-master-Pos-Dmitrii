from unittest.mock import Mock
import pytest
from task_app.models.tasks import Task
from task_app.schemas.tasks import CreateTaskRequest, UpdateTaskRequest
from task_app.services.tasks import TaskService

def test_create_task_with_mock_repo():
    """
    Тест сервиса с моком репозитория (по слайду 9 лекции 7).
    База данных не запускается — тест быстрый, проверяет вызовы и возвращаемое значение.
    """
    mock_repo = Mock()
    mock_repo.count.return_value = 0
    mock_repo.create.return_value = Task(
        id=1,
        title="Купить молоко",
        description="2 пакета",
        priority=2,
        done=False
    )
    mock_notifier = Mock()

    service = TaskService(repo=mock_repo, notifier=mock_notifier)
    data = CreateTaskRequest(title="Купить молоко", description="2 пакета", priority=2)
    
    result = service.create_task(data)

    mock_repo.create.assert_called_once()
    mock_notifier.notify.assert_called_once()
    assert result.id == 1
    assert result.title == "Купить молоко"

def test_create_task_validation_empty_title():
    """Проверка, что пустой title выбрасывает ValueError в сервисном слое."""
    mock_repo = Mock()
    mock_repo.count.return_value = 0
    service = TaskService(repo=mock_repo)

    data = CreateTaskRequest(title="  ", priority=1)
    with pytest.raises(ValueError, match="не менее 3 символов"):
        service.create_task(data)

def test_task_limit_exceeded():
    """Проверка бизнес-правила лимита в 100 задач (слайд 8 лекции 7А)."""
    mock_repo = Mock()
    mock_repo.count.return_value = 100
    service = TaskService(repo=mock_repo)

    data = CreateTaskRequest(title="Новая задача", priority=1)
    with pytest.raises(ValueError, match="лимит в 100 задач"):
        service.create_task(data)

def test_get_task_not_found():
    """Проверка ошибки при поиске несуществующей задачи."""
    mock_repo = Mock()
    mock_repo.get_by_id.return_value = None
    service = TaskService(repo=mock_repo)

    with pytest.raises(ValueError, match="не найдена"):
        service.get_task_by_id(999)
