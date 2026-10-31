import boto3
from botocore.client import BaseClient
from botocore.config import Config
from task_app.core.config import get_settings


def create_s3_client() -> BaseClient:
    """Фабрика клиента boto3. Для локального хранилища и облака отличается только endpoint и ключи."""
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,  # http:// или https:// задаёт протокол
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,  # регион входит в подпись
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},  # бакет в пути URL
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
