from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50, description="Имя пользователя")
    email: str = Field(description="Email пользователя")

class UserCreate(UserBase):
    password: str = Field(min_length=6, description="Пароль пользователя")

class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
