import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from task_app.core.database import Base, get_db
from task_app.core.security import hash_password, verify_password, create_access_token
from task_app.main import app
from task_app.models.users import User

# Отдельная БД в памяти: тесты не трогают tasks.db
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

ALICE = {"username": "alice", "email": "alice@example.com", "password": "secret123"}

def register_and_login(client, user=ALICE) -> dict:
    client.post("/v1/auth/register", json=user)
    resp = client.post("/v1/auth/login", data={"username": user["username"], "password": user["password"]})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

def make_admin(username: str) -> None:
    db = TestingSessionLocal()
    db.query(User).filter(User.username == username).update({"role": "admin"})
    db.commit()
    db.close()


# --- security.py ---

def test_hash_password_is_salted():
    """hash_password дважды даёт разные строки, verify_password возвращает True."""
    h1, h2 = hash_password("secret123"), hash_password("secret123")
    assert h1 != h2
    assert verify_password("secret123", h1)
    assert not verify_password("wrong", h1)


# --- Четыре сценария со слайда 34 ---

def test_register_stores_hash_not_password(client):
    resp = client.post("/v1/auth/register", json=ALICE)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "user"
    assert "password" not in body and "hashed_password" not in body

    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "alice").first()
    db.close()
    assert user.hashed_password != "secret123"
    assert verify_password("secret123", user.hashed_password)

def test_login_returns_token(client):
    client.post("/v1/auth/register", json=ALICE)
    resp = client.post("/v1/auth/login", data={"username": "alice", "password": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["access_token"]

def test_tasks_with_token(client):
    headers = register_and_login(client)
    resp = client.get("/v1/tasks", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_tasks_without_token(client):
    assert client.get("/v1/tasks").status_code == 401


# --- Ошибки аутентификации ---

def test_register_duplicate_username(client):
    client.post("/v1/auth/register", json=ALICE)
    resp = client.post("/v1/auth/register", json={**ALICE, "email": "other@example.com"})
    assert resp.status_code == 400

def test_login_wrong_password_and_unknown_user_same_error(client):
    client.post("/v1/auth/register", json=ALICE)
    wrong_pwd = client.post("/v1/auth/login", data={"username": "alice", "password": "nope"})
    no_user = client.post("/v1/auth/login", data={"username": "bob", "password": "nope"})
    assert wrong_pwd.status_code == no_user.status_code == 401
    assert wrong_pwd.json()["detail"] == no_user.json()["detail"]

def test_invalid_and_expired_token(client):
    client.post("/v1/auth/register", json=ALICE)
    bad = client.get("/v1/tasks", headers={"Authorization": "Bearer not-a-jwt"})
    expired_token = create_access_token({"sub": "alice"}, expires_minutes=-1)
    expired = client.get("/v1/tasks", headers={"Authorization": f"Bearer {expired_token}"})
    assert bad.status_code == 401
    assert expired.status_code == 401

def test_me(client):
    headers = register_and_login(client)
    resp = client.get("/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


# --- Авторизация по ролям ---

def test_user_cannot_delete_task(client):
    headers = register_and_login(client)
    task = client.post("/v1/tasks", json={"title": "Задача alice"}, headers=headers).json()
    resp = client.delete(f"/v1/tasks/{task['id']}", headers=headers)
    assert resp.status_code == 403

def test_admin_can_delete_task(client):
    headers = register_and_login(client)
    make_admin("alice")
    task = client.post("/v1/tasks", json={"title": "Задача alice"}, headers=headers).json()
    assert client.delete(f"/v1/tasks/{task['id']}", headers=headers).status_code == 204

def test_users_list_only_for_admin(client):
    headers = register_and_login(client)
    assert client.get("/v1/users", headers=headers).status_code == 403
    make_admin("alice")
    resp = client.get("/v1/users", headers=headers)
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["alice"]
