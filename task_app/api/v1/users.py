from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from task_app.core.database import get_db
from task_app.schemas.users import UserCreate, UserResponse
from task_app.repositories.users import UserRepository
from task_app.services.users import UserService

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, service: UserService = Depends(get_user_service)):
    try:
        return service.create_user(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

@router.get("", response_model=List[UserResponse])
def get_all_users(service: UserService = Depends(get_user_service)):
    return service.get_all_users()
