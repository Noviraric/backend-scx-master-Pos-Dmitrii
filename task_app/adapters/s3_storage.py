from typing import Optional
from urllib.parse import quote
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
from task_app.adapters.file_storage import FileStorage, FileStorageError, StoredFileNotFound

_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound"}


class S3Storage(FileStorage):
    """Адаптер: приводит boto3 к интерфейсу FileStorage и переводит его ошибки в наши."""

    def __init__(self, client: BaseClient, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def upload(self, key: str, data: bytes, content_type: str,
               metadata: Optional[dict[str, str]] = None) -> str:
        params = {"Bucket": self._bucket, "Key": key, "Body": data, "ContentType": content_type}
        if metadata:
            # HTTP-заголовки допускают только ASCII — кириллицу в имени файла кодируем
            params["Metadata"] = {k.lower(): quote(str(v)) for k, v in metadata.items()}
        try:
            self._client.put_object(**params)
        except (ClientError, BotoCoreError) as e:
            raise FileStorageError(f"Не удалось сохранить {key}") from e
        return key

    def get_download_url(self, key: str, expires_in: int = 3600) -> str:
        # Подпись считается локально и не ходит в сеть, поэтому существование проверяем сами
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] in _NOT_FOUND_CODES:
                raise StoredFileNotFound(key) from e
            raise FileStorageError(f"Ошибка доступа к {key}") from e
        except BotoCoreError as e:
            raise FileStorageError("Хранилище недоступно") from e
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (ClientError, BotoCoreError) as e:
            raise FileStorageError(f"Не удалось удалить {key}") from e
