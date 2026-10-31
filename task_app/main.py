from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from task_app.core.config import get_settings
from task_app.core.database import Base, engine
from task_app.core.handlers import register_exception_handlers
from task_app.api.v1.tasks import router as tasks_v1_router
from task_app.api.v1.users import router as users_v1_router
from task_app.api.v1.auth import router as auth_v1_router
from task_app import models  # noqa: F401 — регистрируем все модели до create_all

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте создаём таблицы. create_all синхронный API, поэтому через run_sync
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    db_url = engine.url.render_as_string(hide_password=True)  # пароль в лог не пишем
    print(f"[STARTUP] База данных инициализирована. Таблицы созданы в {db_url}")
    yield
    await engine.dispose()  # при остановке закрываем соединения пула
    print("[SHUTDOWN] Остановка приложения.")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Учебный проект: асинхронный таск-трекер (FastAPI + SQLAlchemy async), "
                "JWT-аутентификация, аватарки задач в S3 и единый формат ошибок "
                '{"error": {"code", "message", "field", "details"}}.',
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Разрешаем CORS для взаимодействия с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Единый формат ошибок для всех входов: наши исключения, валидация, 404/405, БД, S3, всё прочее
register_exception_handlers(app)

# Подключение роутеров API v1
app.include_router(
    auth_v1_router,
    prefix="/v1",
)
app.include_router(
    tasks_v1_router,
    prefix="/v1",
)
app.include_router(
    users_v1_router,
    prefix="/v1",
)

@app.get("/", tags=["health"])
async def root():
    """Корневой эндпоинт проверки статуса API."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "endpoints": {
            "register": "POST /v1/auth/register",
            "login": "POST /v1/auth/login",
            "me": "GET /v1/auth/me",
            "create_task": "POST /v1/tasks",
            "get_all_tasks": "GET /v1/tasks",
            "get_task_by_id": "GET /v1/tasks/{id}",
            "update_task": "PUT /v1/tasks/{id}",
            "delete_task": "DELETE /v1/tasks/{id}",
            "upload_avatar": "POST /v1/tasks/{id}/avatar",
            "get_avatar_url": "GET /v1/tasks/{id}/avatar",
            "delete_avatar": "DELETE /v1/tasks/{id}/avatar",
        }
    }
