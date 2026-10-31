from typing import List
from fastapi import APIRouter, Depends
from task_app.dependencies import get_user_repository, require_admin
from task_app.schemas.users import UserResponse
from task_app.repositories.users import UserRepository
from task_app.services.users import UserService

# Регистрация — в /v1/auth/register. Список пользователей видит только admin.
router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_admin)],
)

async def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

@router.get("", response_model=List[UserResponse])
async def get_all_users(service: UserService = Depends(get_user_service)):
    return await service.get_all_users()
