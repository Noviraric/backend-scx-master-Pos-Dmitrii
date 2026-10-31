import asyncio
import jwt
from task_app.core.exceptions import (
    EmailAlreadyExistsException,
    InvalidCredentialsException,
    InvalidTokenException,
    PasswordTooLongException,
    UserAlreadyExistsException,
)
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


class AuthService:
    """
    Регистрация, вход и проверка токена.
    bcrypt специально медленный (сотни мс) — это CPU-работа, поэтому хеширование
    и проверка пароля уходят в поток через asyncio.to_thread и не блокируют цикл событий.
    """

    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def register(self, data: UserCreate) -> User:
        username = data.username.strip()
        email = data.email.strip().lower()
        if await self.repo.get_by_username(username):
            raise UserAlreadyExistsException(username)
        if await self.repo.get_by_email(email):
            raise EmailAlreadyExistsException(email)
        if len(data.password.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise PasswordTooLongException(BCRYPT_MAX_BYTES)
        hashed = await asyncio.to_thread(hash_password, data.password)
        return await self.repo.create(username, email, hashed)

    async def login(self, username: str, password: str) -> str:
        user = await self.repo.get_by_username(username.strip())
        # Одинаковая ошибка для логина и пароля — не подсказываем, что именно неверно
        if not user or not await asyncio.to_thread(verify_password, password, user.hashed_password):
            raise InvalidCredentialsException()
        return create_access_token({"sub": user.username, "role": user.role})

    async def get_user_by_token(self, token: str) -> User:
        try:
            payload = decode_access_token(token)
        except jwt.InvalidTokenError:
            raise InvalidTokenException()
        username = payload.get("sub")
        user = await self.repo.get_by_username(username) if username else None
        if not user:
            raise InvalidTokenException("Пользователь из токена не найден")
        return user
