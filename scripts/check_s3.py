"""
Проверка подключения к S3 и создание бакета, если его нет.
Запуск из корня проекта:  python -m scripts.check_s3
"""
import sys
from botocore.exceptions import BotoCoreError, ClientError
from task_app.adapters.s3_client import create_s3_client
from task_app.core.config import get_settings

def main() -> None:
    settings = get_settings()
    client = create_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
        print(f"✓ Бакет '{settings.s3_bucket}' существует и доступен ({settings.s3_endpoint})")
    except ClientError as e:
        # Ответ на HEAD без тела: код ошибки — HTTP-статус строкой, "404" или "403"
        code = e.response["Error"]["Code"]
        if code in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=settings.s3_bucket)
            print(f"✓ Бакет '{settings.s3_bucket}' создан")
        else:
            print(f"✗ Нет доступа к бакету '{settings.s3_bucket}': {code}")
            sys.exit(1)
    except BotoCoreError as e:
        print(f"✗ Хранилище {settings.s3_endpoint} недоступно: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
