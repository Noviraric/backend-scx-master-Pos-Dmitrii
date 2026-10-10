from typing import List
from task_app.repositories.users import UserRepository
from task_app.schemas.users import UserCreate
from task_app.models.users import User

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_all_users(self) -> List[User]:
        return self.repo.get_all()

    def create_user(self, data: UserCreate) -> User:
        if self.repo.get_by_username(data.username):
            raise ValueError(f"Пользователь с именем '{data.username}' уже существует")
        return self.repo.create(data)
