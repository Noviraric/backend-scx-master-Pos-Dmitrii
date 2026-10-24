from fastapi import APIRouter
from task_app.api.v1.auth import router as auth_router
from task_app.api.v1.tasks import router as tasks_router
from task_app.api.v1.users import router as users_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(users_router)

__all__ = ["api_v1_router", "auth_router", "tasks_router", "users_router"]
