"""Единый формат ошибок (пара 11А): {"error": {"code", "message", "field", "details"}} на всех входах."""
from task_app.dependencies import get_task_service
from task_app.main import app


def assert_error_shape(body: dict) -> dict:
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "field", "details"}
    return body["error"]


async def test_task_not_found_format(client, auth_headers):
    resp = await client.get("/v1/tasks/999", headers=auth_headers)
    assert resp.status_code == 404
    error = assert_error_shape(resp.json())
    assert error["code"] == "TASK_NOT_FOUND"
    assert error["details"] == {"task_id": 999}
    assert "999" in error["message"]

async def test_title_too_short_business_rule(client, auth_headers):
    # 3 пробела проходят Pydantic, но не проходят правило сервиса
    resp = await client.post("/v1/tasks", json={"title": "   "}, headers=auth_headers)
    assert resp.status_code == 400
    error = assert_error_shape(resp.json())
    assert error["code"] == "TASK_TITLE_TOO_SHORT"
    assert error["field"] == "title"

async def test_pydantic_validation_format(client, auth_headers):
    resp = await client.post("/v1/tasks", json={"title": "ab", "priority": 9}, headers=auth_headers)
    assert resp.status_code == 422
    error = assert_error_shape(resp.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert error["field"] == "title"
    assert {e["field"] for e in error["details"]["errors"]} == {"title", "priority"}

async def test_unknown_url(client):
    resp = await client.get("/v1/nope")
    assert resp.status_code == 404
    assert assert_error_shape(resp.json())["code"] == "NOT_FOUND"

async def test_wrong_method(client):
    resp = await client.put("/v1/auth/login")
    assert resp.status_code == 405
    assert assert_error_shape(resp.json())["code"] == "METHOD_NOT_ALLOWED"

async def test_unexpected_error_hides_details(client, auth_headers):
    async def broken_service():
        raise RuntimeError("секретная деталь реализации")

    app.dependency_overrides[get_task_service] = broken_service
    resp = await client.get("/v1/tasks", headers=auth_headers)
    assert resp.status_code == 500
    error = assert_error_shape(resp.json())
    assert error["code"] == "INTERNAL_SERVER_ERROR"
    assert "секретная" not in resp.text  # стек — в лог, клиенту — только код и текст
