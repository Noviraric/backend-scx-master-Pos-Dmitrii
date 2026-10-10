from fastapi import APIRouter
from task_app.api.v1.tasks import router as tasks_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(tasks_router)

__all__ = ["api_v1_router", "tasks_router"]
