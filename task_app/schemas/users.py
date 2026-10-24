from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50, description="Имя пользователя", examples=["alice"])
    email: str = Field(description="Email пользователя", examples=["alice@example.com"])

class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=72, description="Пароль пользователя", examples=["secret123"])

class UserResponse(UserBase):
    """Наружу отдаём пользователя без хеша пароля."""
    id: int
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
