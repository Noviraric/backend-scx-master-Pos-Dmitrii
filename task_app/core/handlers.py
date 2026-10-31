import logging
from typing import Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException
from task_app.adapters.file_storage import FileStorageError
from task_app.core.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)

# Ошибки фреймворка (неизвестный URL, нет токена и т.п.) → наш код и русский текст
_HTTP_ERRORS = {
    status.HTTP_401_UNAUTHORIZED: (ErrorCode.UNAUTHORIZED, "Требуется аутентификация"),
    status.HTTP_403_FORBIDDEN: (ErrorCode.FORBIDDEN, "Доступ запрещён"),
    status.HTTP_404_NOT_FOUND: (ErrorCode.NOT_FOUND, "Ресурс не найден"),
    status.HTTP_405_METHOD_NOT_ALLOWED: (ErrorCode.METHOD_NOT_ALLOWED, "Метод не поддерживается для этого адреса"),
}


def error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    field: Optional[str] = None,
    details: Optional[dict] = None,
    headers: Optional[dict] = None,
) -> JSONResponse:
    """Единый формат ошибки: {"error": {"code", "message", "field", "details"}}."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code.value, "message": message, "field": field, "details": details or {}}},
        headers=headers,
    )


def _field_from_loc(loc: tuple) -> str:
    # ("body", "title") → "title"; ("query", "limit") → "limit"
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header", "cookie")]
    return ".".join(parts) or None


def register_exception_handlers(app: FastAPI) -> None:
    """Единственное место, где решается формат ошибок. Бизнес-код только бросает исключения."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},  # меняем обёртку detail → error
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = [
            {"field": _field_from_loc(err["loc"]), "message": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ]
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorCode.VALIDATION_ERROR,
            "Некорректные данные запроса",
            field=errors[0]["field"] if errors else None,
            details={"errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code, message = _HTTP_ERRORS.get(exc.status_code, (ErrorCode.HTTP_ERROR, str(exc.detail)))
        return error_response(exc.status_code, code, message, headers=getattr(exc, "headers", None))

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        # Например, гонка двух регистраций с одним email — проверка в сервисе её не ловит
        logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
        return error_response(
            status.HTTP_409_CONFLICT,
            ErrorCode.CONFLICT,
            "Запись конфликтует с уже существующими данными",
        )

    @app.exception_handler(FileStorageError)
    async def file_storage_error_handler(request: Request, exc: FileStorageError):
        logger.exception("File storage error on %s %s", request.method, request.url.path)
        return error_response(
            status.HTTP_502_BAD_GATEWAY,
            ErrorCode.FILE_STORAGE_ERROR,
            "Хранилище файлов недоступно",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Стек — в лог, клиенту — только код и общий текст
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_SERVER_ERROR,
            "Внутренняя ошибка сервера",
        )
