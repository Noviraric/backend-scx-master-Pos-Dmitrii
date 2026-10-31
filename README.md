# Task Tracker API — Интеграция БД и полный CRUD для сущности Task

Проект разработан в рамках учебного курса по FastAPI и чистой бэкенд-архитектуре.

## 🚀 Архитектурная цепочка (Слои)

```
Клиент (HTTP / Swagger / Frontend)
       │
       ▼  JSON / HTTP-статусы; ошибки — всегда {"error": {...}}
api/v1/tasks.py (Тонкий async-роут: принимает DTO, await сервис. Ничего не ловит)
       │
       ▼  DTO
services/tasks.py (Async-сервис: бизнес-правила, лимиты, аватарки. Бросает AppException-ы)
       │                         │
       ▼  await repo.*()         ▼  asyncio.to_thread(storage.*) — boto3 синхронный
repositories/tasks.py       adapters/ (FileStorage → S3Storage → boto3)
       │
       ▼  AsyncSession (per-request через Depends(get_db))
core/database.py + models/ (PostgreSQL через asyncpg / SQLite через aiosqlite)

core/handlers.py — единственное место, где исключения превращаются в JSON-ответ
```

## ⚡ Асинхронность

- Весь стек `async def`: роуты → сервисы → репозитории → `AsyncSession` (SQLAlchemy 2.x).
- Драйверы: `postgresql+asyncpg://...` и `sqlite+aiosqlite:///...`. Старые URL (`postgresql+psycopg2://`, `sqlite:///`)
  автоматически переводятся на async-драйвер в `core/config.py`.
- Блокирующая работа уходит из цикла событий в поток через `asyncio.to_thread`: bcrypt (медленный намеренно) и boto3 (синхронный).
- Таблицы создаются при старте: `await conn.run_sync(Base.metadata.create_all)`; при остановке — `engine.dispose()`.

## ❗ Обработка ошибок

Любая ошибка API имеет один формат:

```json
{"error": {"code": "TASK_NOT_FOUND", "message": "Задача с идентификатором 999 не найдена", "field": null, "details": {"task_id": 999}}}
```

- `code` — для программы (switch, перевод), `message` — для человека, `field` — какое поле подсветить, `details` — контекст.
- Коды — `ErrorCode` в `core/exceptions.py`, исключения — наследники `AppException` (`TaskNotFoundException`, `UserAlreadyExistsException`, ...).
- Обработчики в `core/handlers.py` закрывают все входы:

| Исключение | Статус | Код |
|---|---|---|
| `AppException` и наследники | из класса | `TASK_NOT_FOUND`, `USER_ALREADY_EXISTS`, `INVALID_FILE`, ... |
| `RequestValidationError` (Pydantic) | 422 | `VALIDATION_ERROR` + `details.errors` |
| Неизвестный URL / метод / нет токена | 404 / 405 / 401 | `NOT_FOUND` / `METHOD_NOT_ALLOWED` / `UNAUTHORIZED` |
| `IntegrityError` (БД) | 409 | `CONFLICT` |
| `FileStorageError` (S3) | 502 | `FILE_STORAGE_ERROR` |
| Всё прочее | 500 | `INTERNAL_SERVER_ERROR` (стек — только в лог) |

## 🖼 Аватарки задач в S3

| Метод | URL | Ответ |
|---|---|---|
| `POST` | `/v1/tasks/{task_id}/avatar` | 200 `{task_id, key, url}`; 400 не изображение / пустой; 413 > 5 МБ; 404 нет задачи; 502 хранилище недоступно |
| `GET` | `/v1/tasks/{task_id}/avatar` | 200 новая подписанная ссылка (1 час); 404 `AVATAR_NOT_SET` |
| `DELETE` | `/v1/tasks/{task_id}/avatar` | 204; 404 `AVATAR_NOT_SET` |

- Тип файла — по сигнатуре (PNG, JPEG, GIF), а не по `Content-Type`. Читается не больше 5 МБ + 1 байт.
- Ключ строит сервер: `tasks/{id}/avatar.{ext}`. В БД (`tasks.avatar_key`) хранится ключ, ссылка генерируется при каждом запросе.
- Бакет приватный, доступ только по подписанным URL. Сервис знает лишь интерфейс `FileStorage` — в тестах подставляется хранилище-словарь.

**Локальное хранилище (Docker):**
```bash
docker run -d --name minio -p 9000:9000 -p 9001:9001 -v minio_data:/data -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin pgsty/silo:RELEASE.2026-09-16T00-00-00Z server /data --console-address ":9001"
python -m scripts.check_s3        # проверит подключение и создаст бакет task-avatars
```
Консоль хранилища: http://localhost:9001. Переменные `S3_*` — в `.env` (образец — `.env.example`).

## 🛠 Реализованный CRUD для сущности Task

| Метод | URL | Описание | Код ответа |
|---|---|---|---|
| `POST` | `/v1/tasks` | **Create**: Создание новой задачи (с валидацией через `CreateTaskRequest`) | `201 Created` |
| `GET` | `/v1/tasks` | **Read Collection**: Получение всех задач (поддержка `skip` и `limit`) | `200 OK` |
| `GET` | `/v1/tasks/{task_id}` | **Read Single**: Получение одной задачи по её `id` | `200 OK` / `404 Not Found` |
| `PUT` | `/v1/tasks/{task_id}` | **Update**: Полное/частичное обновление задачи (`UpdateTaskRequest`) | `200 OK` / `404 Not Found` |
| `PATCH`| `/v1/tasks/{task_id}` | **Update**: Частичное обновление задачи | `200 OK` / `404 Not Found` |
| `DELETE`| `/v1/tasks/{task_id}` | **Delete**: Удаление задачи из БД по `id` | `204 No Content` / `404 Not Found` |

## 🔐 Аутентификация и авторизация (JWT)

| Метод | URL | Доступ | Описание |
|---|---|---|---|
| `POST` | `/v1/auth/register` | все | Регистрация (JSON: `username`, `email`, `password`). В БД — bcrypt-хеш |
| `POST` | `/v1/auth/login` | все | Вход (form-data: `username`, `password`) → `access_token` (JWT, 30 мин) |
| `GET` | `/v1/auth/me` | с токеном | Текущий пользователь |
| `*` | `/v1/tasks...` | с токеном | Все операции с задачами, кроме удаления |
| `DELETE` | `/v1/tasks/{task_id}` | admin | Удаление задачи |
| `GET` | `/v1/users` | admin | Список пользователей |

- Запросы с токеном: заголовок `Authorization: Bearer <token>`. В Swagger — кнопка **Authorize**.
- Без токена — `401 UNAUTHORIZED`, невалидный токен — `401 INVALID_TOKEN`, без нужной роли — `403 PERMISSION_DENIED`, имя или email заняты — `409`.
- Выдать роль admin: `python -m task_app.make_admin <username>`.
- Секрет подписи задаётся в `.env`: `SECRET_KEY=...` (а также `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`).

## 📦 Быстрый запуск на локальной машине

1. Установка виртуального окружения и зависимостей:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Для Linux/macOS
   # или .venv\Scripts\activate для Windows
   pip install -r requirements.txt
   copy .env.example .env             # и заполнить значения
   ```

2. Запуск сервера с автоперезагрузкой:
   ```bash
   uvicorn task_app.main:app --reload
   ```

   Или `python server.py` — если в папке `certs/` есть сертификаты, сервер запустится по HTTPS.

   **Локальный HTTPS (один раз):**
   ```bash
   winget install FiloSottile.mkcert
   mkcert -install                     # доверенный локальный CA в системе
   mkdir certs
   mkcert -cert-file certs/localhost.pem -key-file certs/localhost-key.pem localhost 127.0.0.1 ::1
   python server.py                    # → https://localhost:8000/docs
   ```
   Папка `certs/` в `.gitignore` — закрытый ключ в репозиторий не попадает.

3. Открыть документацию Swagger UI:
   - [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

4. Запуск тестов (БД — SQLite в памяти, S3 — словарь; ни PostgreSQL, ни Docker не нужны):
   ```bash
   pytest -v
   ```
