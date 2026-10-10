from typing import List, Optional
from sqlalchemy.orm import Session
from task_app.models.users import User
from task_app.schemas.users import UserCreate

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[User]:
        return self.db.query(User).all()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def create(self, user_data: UserCreate) -> User:
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=f"hash_{user_data.password}",
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
