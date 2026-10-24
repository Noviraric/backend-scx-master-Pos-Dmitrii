from typing import List, Optional
from sqlalchemy.orm import Session
from task_app.models.users import User

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[User]:
        return self.db.query(User).all()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def create(self, username: str, email: str, hashed_password: str) -> User:
        """Создать пользователя. Пароль сюда приходит уже захешированным."""
        db_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def set_role(self, user: User, role: str) -> User:
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user
