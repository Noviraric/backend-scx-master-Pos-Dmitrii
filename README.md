# Task Tracker API — Интеграция БД и полный CRUD для сущности Task

Проект разработан в рамках учебного курса по FastAPI и чистой бэкенд-архитектуре.

## 🚀 Архитектурная цепочка (Слои)

```
Клиент (HTTP / Swagger / Frontend)
       │
       ▼  JSON / HTTP-статусы
api/v1/tasks.py (Тонкий роут-адаптер: принимает DTO, вызывает сервис, ловит ValueError -> 422/404)
       │
       ▼  DTO / Чистый Python (без зависимостей от FastAPI)
services/tasks.py (Толстый сервис: бизнес-правила, валидация, лимиты, вызов Notifier)
       │
       ▼  Методы репозитория (get_all, get_by_id, create, update, delete)
repositories/tasks.py (Репозиторий: запросы SQLAlchemy к БД, add, commit, refresh)
       │
       ▼  Сессия SQLAlchemy (SessionLocal / per-request через Depends(get_db))
core/database.py + models/tasks.py (SQLite / PostgreSQL база данных)
```

## 🛠 Реализованный CRUD для сущности Task

| Метод | URL | Описание | Код ответа |
|---|---|---|---|
| `POST` | `/v1/tasks` | **Create**: Создание новой задачи (с валидацией через `CreateTaskRequest`) | `201 Created` |
| `GET` | `/v1/tasks` | **Read Collection**: Получение всех задач (поддержка `skip` и `limit`) | `200 OK` |
| `GET` | `/v1/tasks/{task_id}` | **Read Single**: Получение одной задачи по её `id` | `200 OK` / `404 Not Found` |
| `PUT` | `/v1/tasks/{task_id}` | **Update**: Полное/частичное обновление задачи (`UpdateTaskRequest`) | `200 OK` / `404 Not Found` |
| `PATCH`| `/v1/tasks/{task_id}` | **Update**: Частичное обновление задачи | `200 OK` / `404 Not Found` |
| `DELETE`| `/v1/tasks/{task_id}` | **Delete**: Удаление задачи из БД по `id` | `204 No Content` / `404 Not Found` |

## 📦 Быстрый запуск на локальной машине

1. Установка виртуального окружения и зависимостей:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Для Linux/macOS
   # или .venv\Scripts\activate для Windows
   pip install -r requirements.txt
   ```

2. Запуск сервера с автоперезагрузкой:
   ```bash
   uvicorn task_app.main:app --reload
   ```

3. Открыть документацию Swagger UI:
   - [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

4. Запуск тестов:
   ```bash
   pytest tests/ -v
   ```
