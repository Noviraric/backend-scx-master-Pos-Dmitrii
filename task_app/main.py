from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from task_app.core.config import get_settings
from task_app.core.database import Base, engine
from task_app.api.v1.tasks import router as tasks_v1_router
from task_app.api.v1.users import router as users_v1_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Автоматическое создание таблиц в базе данных при старте
    Base.metadata.create_all(bind=engine)
    print(f"[STARTUP] База данных инициализирована. Таблицы созданы в {settings.database_url}")
    yield
    print("[SHUTDOWN] Остановка приложения.")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Учебный проект: Таск-трекер с базой данных (SQLAlchemy) и полным CRUD для сущности Task.",
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

# Подключение роутеров API v1
app.include_router(
    tasks_v1_router,
    prefix="/v1",
)
app.include_router(
    users_v1_router,
    prefix="/v1",
)

@app.get("/", tags=["health"])
def root():
    """Корневой эндпоинт проверки статуса API."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "endpoints": {
            "create_task": "POST /v1/tasks",
            "get_all_tasks": "GET /v1/tasks",
            "get_task_by_id": "GET /v1/tasks/{id}",
            "update_task": "PUT /v1/tasks/{id}",
            "delete_task": "DELETE /v1/tasks/{id}",
        }
    }
