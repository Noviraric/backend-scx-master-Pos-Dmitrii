import jwt
from task_app.core.security import (
    BCRYPT_MAX_BYTES,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from task_app.models.users import User
from task_app.repositories.users import UserRepository
from task_app.schemas.users import UserCreate


class AuthenticationError(Exception):
    """Неверный логин/пароль или невалидный токен (роут превращает в 401)."""


class AuthService:
    """
    Регистрация, вход и проверка токена.
    Как и TaskService — чистый Python без FastAPI: ошибки данных — ValueError,
    ошибки входа — AuthenticationError.
    """

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def register(self, data: UserCreate) -> User:
        username = data.username.strip()
        email = data.email.strip().lower()
        if self.repo.get_by_username(username):
            raise ValueError(f"Пользователь с именем '{username}' уже существует")
        if self.repo.get_by_email(email):
            raise ValueError(f"Email '{email}' уже занят")
        if len(data.password.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError(f"Пароль не может быть длиннее {BCRYPT_MAX_BYTES} байт")
        return self.repo.create(username, email, hash_password(data.password))

    def login(self, username: str, password: str) -> str:
        user = self.repo.get_by_username(username.strip())
        # Одинаковая ошибка для логина и пароля — не подсказываем, что именно неверно
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Неверное имя пользователя или пароль")
        return create_access_token({"sub": user.username, "role": user.role})

    def get_user_by_token(self, token: str) -> User:
        try:
            payload = decode_access_token(token)
        except jwt.InvalidTokenError:
            raise AuthenticationError("Невалидный или просроченный токен")
        username = payload.get("sub")
        user = self.repo.get_by_username(username) if username else None
        if not user:
            raise AuthenticationError("Пользователь из токена не найден")
        return user
