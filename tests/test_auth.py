from sqlalchemy import select
from task_app.core.security import hash_password, verify_password, create_access_token
from task_app.models.users import User
from tests.conftest import ALICE, register_and_login


# --- security.py ---

def test_hash_password_is_salted():
    """hash_password дважды даёт разные строки, verify_password возвращает True."""
    h1, h2 = hash_password("secret123"), hash_password("secret123")
    assert h1 != h2
    assert verify_password("secret123", h1)
    assert not verify_password("wrong", h1)


# --- Четыре сценария со слайда 34 пары 9Б ---

async def test_register_stores_hash_not_password(client, session_factory):
    resp = await client.post("/v1/auth/register", json=ALICE)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "user"
    assert "password" not in body and "hashed_password" not in body

    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.username == "alice"))).scalar_one()
    assert user.hashed_password != "secret123"
    assert verify_password("secret123", user.hashed_password)

async def test_login_returns_token(client):
    await client.post("/v1/auth/register", json=ALICE)
    resp = await client.post("/v1/auth/login", data={"username": "alice", "password": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["access_token"]

async def test_tasks_with_token(client, auth_headers):
    resp = await client.get("/v1/tasks", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

async def test_tasks_without_token(client):
    resp = await client.get("/v1/tasks")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# --- Ошибки аутентификации ---

async def test_register_duplicate_username(client):
    await client.post("/v1/auth/register", json=ALICE)
    resp = await client.post("/v1/auth/register", json={**ALICE, "email": "other@example.com"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "USER_ALREADY_EXISTS"
    assert resp.json()["error"]["field"] == "username"

async def test_register_duplicate_email(client):
    await client.post("/v1/auth/register", json=ALICE)
    resp = await client.post("/v1/auth/register", json={**ALICE, "username": "alice2"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

async def test_login_wrong_password_and_unknown_user_same_error(client):
    await client.post("/v1/auth/register", json=ALICE)
    wrong_pwd = await client.post("/v1/auth/login", data={"username": "alice", "password": "nope"})
    no_user = await client.post("/v1/auth/login", data={"username": "bob", "password": "nope"})
    assert wrong_pwd.status_code == no_user.status_code == 401
    assert wrong_pwd.json() == no_user.json()
    assert wrong_pwd.json()["error"]["code"] == "INVALID_CREDENTIALS"

async def test_invalid_and_expired_token(client):
    await client.post("/v1/auth/register", json=ALICE)
    bad = await client.get("/v1/tasks", headers={"Authorization": "Bearer not-a-jwt"})
    expired_token = create_access_token({"sub": "alice"}, expires_minutes=-1)
    expired = await client.get("/v1/tasks", headers={"Authorization": f"Bearer {expired_token}"})
    assert bad.status_code == expired.status_code == 401
    assert bad.json()["error"]["code"] == expired.json()["error"]["code"] == "INVALID_TOKEN"
    assert bad.headers["www-authenticate"] == "Bearer"

async def test_me(client, auth_headers):
    resp = await client.get("/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


# --- Авторизация по ролям ---

async def test_user_cannot_delete_task(client, auth_headers):
    task = (await client.post("/v1/tasks", json={"title": "Задача alice"}, headers=auth_headers)).json()
    resp = await client.delete(f"/v1/tasks/{task['id']}", headers=auth_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"

async def test_admin_can_delete_task(client, auth_headers, make_admin):
    await make_admin("alice")
    task = (await client.post("/v1/tasks", json={"title": "Задача alice"}, headers=auth_headers)).json()
    assert (await client.delete(f"/v1/tasks/{task['id']}", headers=auth_headers)).status_code == 204

async def test_users_list_only_for_admin(client, auth_headers, make_admin):
    assert (await client.get("/v1/users", headers=auth_headers)).status_code == 403
    await make_admin("alice")
    resp = await client.get("/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["alice"]
