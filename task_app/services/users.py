from typing import List
from task_app.repositories.users import UserRepository
from task_app.models.users import User

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_all_users(self) -> List[User]:
        return self.repo.get_all()
