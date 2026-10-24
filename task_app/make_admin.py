"""
Выдать пользователю роль admin.
Запуск из корня проекта:  python -m task_app.make_admin alice
"""
import sys
from task_app.core.database import Base, SessionLocal, engine
from task_app.models import Task, User  # noqa: F401 — регистрируем таблицы для create_all
from task_app.repositories.users import UserRepository

def main() -> None:
    if len(sys.argv) != 2:
        print("Использование: python -m task_app.make_admin <username>")
        sys.exit(1)

    username = sys.argv[1]
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        user = repo.get_by_username(username)
        if not user:
            print(f"Пользователь '{username}' не найден — сначала зарегистрируйте его")
            sys.exit(1)
        repo.set_role(user, "admin")
        print(f"Пользователь '{username}' теперь admin")
    finally:
        db.close()

if __name__ == "__main__":
    main()
