from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from task_app.core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    priority = Column(Integer, default=1, nullable=False)
    done = Column(Boolean, default=False, nullable=False)
    avatar_key = Column(String(1024), nullable=True)  # ключ объекта в S3, не URL; 1024 — максимум длины ключа
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', done={self.done}, priority={self.priority})>"
