from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from task_app.core.config import get_settings

settings = get_settings()

# bcrypt учитывает только первые 72 байта пароля, а bcrypt>=5 на более длинных падает
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Хеш пароля через bcrypt. Соль генерируется автоматически и хранится внутри хеша."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Сверка введённого пароля с хешем из БД."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Слишком длинный пароль или повреждённый хеш — считаем, что пароль неверный
        return False


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    """Подписанный JWT с полем exp (срок жизни из настроек)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Проверка подписи и срока жизни. При любой ошибке — jwt.InvalidTokenError."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
