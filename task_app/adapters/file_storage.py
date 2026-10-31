from abc import ABC, abstractmethod
from typing import Optional


class FileStorageError(Exception):
    """Хранилище недоступно или вернуло ошибку."""


class StoredFileNotFound(FileStorageError):
    """Объекта с таким ключом нет."""


class FileStorage(ABC):
    """
    Интерфейс хранилища файлов в терминах предметной области.
    Сервис знает только его — тесты подставляют мок, смена провайдера не трогает сервис.
    Методы синхронные (boto3 синхронный): из async-кода их вызывают через asyncio.to_thread.
    """

    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str,
               metadata: Optional[dict[str, str]] = None) -> str:
        """Сохраняет объект и возвращает его ключ."""

    @abstractmethod
    def get_download_url(self, key: str, expires_in: int = 3600) -> str:
        """Возвращает временную ссылку для скачивания."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Удаляет объект. Идемпотентно: отсутствие объекта — не ошибка."""
