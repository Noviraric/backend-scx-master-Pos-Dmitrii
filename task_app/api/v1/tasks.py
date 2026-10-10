from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from task_app.schemas.tasks import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskResponse,
)
from task_app.services.tasks import TaskService
from task_app.dependencies import get_task_service

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)

@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую задачу",
    description="Валидирует данные через Pydantic DTO (CreateTaskRequest) и создает запись в БД."
)
def create_task(
    data: CreateTaskRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Создание задачи (Create)."""
    try:
        return service.create_task(data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)
        )

@router.get(
    "",
    response_model=List[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Получить список всех задач (Коллекция)",
    description="Возвращает коллекцию всех задач из базы данных с поддержкой пагинации."
)
def get_all_tasks(
    skip: int = Query(default=0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(default=100, ge=1, le=500, description="Максимальное количество записей"),
    service: TaskService = Depends(get_task_service),
) -> List[TaskResponse]:
    """Чтение коллекции (Read all)."""
    try:
        return service.get_all_tasks(skip=skip, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )

@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить задачу по ID (Один объект)",
    description="Возвращает одну конкретную задачу по ее первичному ключу ID из БД."
)
def get_task_by_id(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Чтение одного объекта (Read single)."""
    try:
        return service.get_task_by_id(task_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )

@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновить задачу по ID",
    description="Обновляет переданные поля задачи (title, description, priority, done) в БД."
)
def update_task(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    data: UpdateTaskRequest = ...,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Обновление задачи (Update)."""
    try:
        return service.update_task(task_id, data)
    except ValueError as exc:
        err_msg = str(exc)
        if "не найдена" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err_msg)

@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Частично обновить задачу по ID",
    description="Аналог PUT для частичного обновления полей задачи."
)
def patch_task(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    data: UpdateTaskRequest = ...,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Частичное обновление задачи (Partial Update)."""
    return update_task(task_id, data, service)

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить задачу по ID",
    description="Удаляет задачу из базы данных по ее идентификатору."
)
def delete_task(
    task_id: int = Path(..., ge=1, description="ID задачи"),
    service: TaskService = Depends(get_task_service),
):
    """Удаление задачи (Delete)."""
    try:
        service.delete_task(task_id)
        return None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )
