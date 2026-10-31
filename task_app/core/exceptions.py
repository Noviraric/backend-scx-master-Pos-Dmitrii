from enum import Enum
from typing import Optional
from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    """Машинные коды ошибок. Клиент делает по ним switch и подставляет перевод."""
    # Общие — их выставляют глобальные обработчики
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    HTTP_ERROR = "HTTP_ERROR"
    CONFLICT = "CONFLICT"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    # Задачи
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_TITLE_TOO_SHORT = "TASK_TITLE_TOO_SHORT"
    TASK_LIMIT_EXCEEDED = "TASK_LIMIT_EXCEEDED"
    INVALID_PAGINATION = "INVALID_PAGINATION"
    # Пользователи и доступ
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    PASSWORD_TOO_LONG = "PASSWORD_TOO_LONG"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    INVALID_TOKEN = "INVALID_TOKEN"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    # Файлы
    INVALID_FILE = "INVALID_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    AVATAR_NOT_SET = "AVATAR_NOT_SET"
    AVATAR_NOT_FOUND = "AVATAR_NOT_FOUND"
    FILE_STORAGE_ERROR = "FILE_STORAGE_ERROR"


class AppException(HTTPException):
    """
    Базовое исключение приложения.
    Наследуется от HTTPException — FastAPI обработает его даже без нашего обработчика,
    а register_exception_handlers меняет обёртку {"detail": ...} на {"error": ...}.
    """

    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict] = None,
        headers: Optional[dict] = None,
    ):
        self.error_code = error_code
        super().__init__(
            status_code=status_code,
            headers=headers,
            detail={
                "code": error_code.value,
                "message": message,
                "field": field,
                "details": details or {},
            },
        )


# --- Задачи ---

class TaskNotFoundException(AppException):
    def __init__(self, task_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.TASK_NOT_FOUND,
            message=f"Задача с идентификатором {task_id} не найдена",
            details={"task_id": task_id},
        )


class TaskTitleTooShortException(AppException):
    def __init__(self, min_length: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.TASK_TITLE_TOO_SHORT,
            message=f"Название задачи должно быть не короче {min_length} символов",
            field="title",
            details={"min_length": min_length},
        )


class TaskLimitExceededException(AppException):
    def __init__(self, limit: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.TASK_LIMIT_EXCEEDED,
            message=f"Достигнут системный лимит в {limit} задач",
            details={"limit": limit},
        )


class InvalidPaginationException(AppException):
    def __init__(self, field: str, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.INVALID_PAGINATION,
            message=message,
            field=field,
        )


# --- Пользователи и доступ ---

class UserAlreadyExistsException(AppException):
    def __init__(self, username: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.USER_ALREADY_EXISTS,
            message=f"Пользователь с именем '{username}' уже существует",
            field="username",
            details={"username": username},
        )


class EmailAlreadyExistsException(AppException):
    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
            message=f"Email '{email}' уже занят",
            field="email",
            details={"email": email},
        )


class PasswordTooLongException(AppException):
    def __init__(self, max_bytes: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.PASSWORD_TOO_LONG,
            message=f"Пароль не может быть длиннее {max_bytes} байт",
            field="password",
            details={"max_bytes": max_bytes},
        )


class InvalidCredentialsException(AppException):
    def __init__(self):
        # Одинаковая ошибка для логина и пароля — не подсказываем, что именно неверно
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.INVALID_CREDENTIALS,
            message="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenException(AppException):
    def __init__(self, message: str = "Невалидный или просроченный токен"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.INVALID_TOKEN,
            message=message,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedException(AppException):
    def __init__(self, required_role: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.PERMISSION_DENIED,
            message=f"Недостаточно прав: требуется роль {required_role}",
            details={"required_role": required_role},
        )


# --- Файлы ---

class InvalidFileException(AppException):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.INVALID_FILE,
            message=message,
            field="file",
            details=details,
        )


class FileTooLargeException(AppException):
    def __init__(self, max_bytes: int):
        super().__init__(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            error_code=ErrorCode.FILE_TOO_LARGE,
            message=f"Файл больше {max_bytes // (1024 * 1024)} МБ",
            field="file",
            details={"max_bytes": max_bytes},
        )


class AvatarNotSetException(AppException):
    def __init__(self, task_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.AVATAR_NOT_SET,
            message=f"У задачи {task_id} нет аватарки",
            details={"task_id": task_id},
        )


class AvatarNotFoundException(AppException):
    def __init__(self, task_id: int, key: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.AVATAR_NOT_FOUND,
            message=f"Файл аватарки задачи {task_id} не найден в хранилище",
            details={"task_id": task_id, "key": key},
        )
