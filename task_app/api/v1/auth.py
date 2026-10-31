from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from task_app.dependencies import get_auth_service, get_current_user
from task_app.models.users import User
from task_app.schemas.users import UserCreate, UserResponse, Token
from task_app.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    description="Создаёт пользователя. В БД сохраняется bcrypt-хеш пароля, а не сам пароль. "
                "409 — имя или email заняты."
)
async def register(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    return await service.register(data)

@router.post(
    "/login",
    response_model=Token,
    summary="Вход и получение JWT",
    description="Принимает form-data (username, password) — поэтому кнопка Authorize в Swagger работает сама."
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
) -> Token:
    token = await service.login(form.username, form.password)
    return Token(access_token=token)

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Текущий пользователь",
    description="Возвращает пользователя, которому принадлежит токен."
)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return user
