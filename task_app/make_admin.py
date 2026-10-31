"""
Выдать пользователю роль admin.
Запуск из корня проекта:  python -m task_app.make_admin alice
"""
import asyncio
import sys
from task_app.core.database import Base, SessionLocal, engine
from task_app.models import Task, User  # noqa: F401 — регистрируем таблицы для create_all
from task_app.repositories.users import UserRepository

async def make_admin(username: str) -> bool:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        async with SessionLocal() as session:
            repo = UserRepository(session)
            user = await repo.get_by_username(username)
            if not user:
                return False
            await repo.set_role(user, "admin")
            return True
    finally:
        await engine.dispose()

def main() -> None:
    if len(sys.argv) != 2:
        print("Использование: python -m task_app.make_admin <username>")
        sys.exit(1)

    username = sys.argv[1]
    if not asyncio.run(make_admin(username)):
        print(f"Пользователь '{username}' не найден — сначала зарегистрируйте его")
        sys.exit(1)
    print(f"Пользователь '{username}' теперь admin")

if __name__ == "__main__":
    main()
