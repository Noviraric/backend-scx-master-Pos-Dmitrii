from typing import List
from fastapi import APIRouter, Depends, File, Path, Query, UploadFile, status
from task_app.schemas.tasks import (
    AvatarResponse,
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskResponse,
)
from task_app.services.tasks import TaskService, MAX_AVATAR_SIZE
from task_app.dependencies import get_task_service, get_current_user, require_admin

# Все эндпоинты задач — только для аутентифицированных пользователей.
# Роуты ничего не ловят: исключения сервиса превращает в ответ глобальный обработчик.
router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)

@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую задачу",
    description="Валидирует данные через Pydantic DTO (CreateTaskRequest) и создает запись в БД."
)
async def create_task(
    data: CreateTaskRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Создание задачи (Create)."""
    return await service.create_task(data)

@router.get(
    "",
    response_model=List[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Получить список всех задач (Коллекция)",
    description="Возвращает коллекцию всех задач из базы данных с поддержкой пагинации."
)
async def get_all_tasks(
    skip: int = Query(default=0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(default=100, ge=1, le=500, description="Максимальное количество записей"),
    service: TaskService = Depends(get_task_service),
) -> List[TaskResponse]:
    """Чтение коллекции (Read all)."""
    return await service.get_all_tasks(skip=skip, limit=limit)

@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить задачу по ID (Один объект)",
    description="Возвращает одну конкретную задачу по ее первичному ключу ID из БД."
)
async def get_task_by_id(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Чтение одного объекта (Read single)."""
    return await service.get_task_by_id(task_id)

@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновить задачу по ID",
    description="Обновляет переданные поля задачи (title, description, priority, done) в БД."
)
async def update_task(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    data: UpdateTaskRequest = ...,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Обновление задачи (Update)."""
    return await service.update_task(task_id, data)

@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Частично обновить задачу по ID",
    description="Аналог PUT для частичного обновления полей задачи."
)
async def patch_task(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    data: UpdateTaskRequest = ...,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Частичное обновление задачи (Partial Update)."""
    return await service.update_task(task_id, data)

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить задачу по ID",
    description="Удаляет задачу и её аватарку. Доступно только роли admin.",
    dependencies=[Depends(require_admin)],
)
async def delete_task(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    service: TaskService = Depends(get_task_service),
):
    """Удаление задачи (Delete)."""
    await service.delete_task(task_id)

# --- Аватарка задачи в S3 ---

@router.post(
    "/{task_id}/avatar",
    response_model=AvatarResponse,
    summary="Загрузить аватарку задачи",
    description="PNG, JPEG или GIF до 5 МБ. Тип определяется по содержимому файла. "
                "Ошибки: 400 — не изображение или пустой файл, 413 — больше 5 МБ, 404 — нет задачи, 502 — хранилище недоступно."
)
async def upload_task_avatar(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    file: UploadFile = File(..., description="Изображение PNG, JPEG или GIF"),
    service: TaskService = Depends(get_task_service),
) -> AvatarResponse:
    # Читаем не больше лимита + 1 байт: гигабайтный файл не попадёт в память целиком
    data = await file.read(MAX_AVATAR_SIZE + 1)
    key = await service.upload_task_avatar(task_id, data, file.filename or "avatar")
    url = await service.get_task_avatar_url(task_id)
    return AvatarResponse(task_id=task_id, key=key, url=url)

@router.get(
    "/{task_id}/avatar",
    response_model=AvatarResponse,
    summary="Ссылка на аватарку задачи",
    description="При каждом вызове выдаёт новую подписанную ссылку (действует 1 час). 404 — аватарки нет."
)
async def get_task_avatar(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    service: TaskService = Depends(get_task_service),
) -> AvatarResponse:
    task = await service.get_task_by_id(task_id)
    url = await service.get_task_avatar_url(task_id)
    return AvatarResponse(task_id=task_id, key=task.avatar_key, url=url)

@router.delete(
    "/{task_id}/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить аватарку задачи",
    description="Удаляет объект из хранилища и очищает avatar_key. 404 — аватарки нет."
)
async def delete_task_avatar(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    service: TaskService = Depends(get_task_service),
):
    await service.delete_task_avatar(task_id)
