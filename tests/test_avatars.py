"""Аватарка задачи в S3: сценарии приёмки пары 21Б (слайды 54–56) через API с хранилищем-словарём."""
from unittest.mock import Mock
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from task_app.adapters.file_storage import FileStorageError, StoredFileNotFound
from task_app.adapters.s3_storage import S3Storage
from task_app.services.tasks import MAX_AVATAR_SIZE

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


async def create_task(client, headers) -> int:
    resp = await client.post("/v1/tasks", json={"title": "Задача с аватаркой"}, headers=headers)
    return resp.json()["id"]


def upload(client, task_id, data, headers, filename="ok.png"):
    return client.post(f"/v1/tasks/{task_id}/avatar", files={"file": (filename, data, "image/png")}, headers=headers)


async def test_upload_ok(client, auth_headers, storage):
    task_id = await create_task(client, auth_headers)
    resp = await upload(client, task_id, PNG, auth_headers, filename="котик.png")
    assert resp.status_code == 200
    body = resp.json()
    assert body["key"] == f"tasks/{task_id}/avatar.png"
    assert body["url"].startswith("https://storage.test/")

    stored = storage.objects[body["key"]]
    assert stored["content_type"] == "image/png"
    assert stored["metadata"]["original-filename"] == "котик.png"

    task = (await client.get(f"/v1/tasks/{task_id}", headers=auth_headers)).json()
    assert task["avatar_key"] == body["key"]  # в БД ключ, а не URL

async def test_upload_fake_png(client, auth_headers):
    task_id = await create_task(client, auth_headers)
    resp = await upload(client, task_id, b"text renamed to .png", auth_headers, filename="fake.png")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_FILE"
    assert resp.json()["error"]["field"] == "file"

async def test_upload_too_large(client, auth_headers):
    task_id = await create_task(client, auth_headers)
    resp = await upload(client, task_id, PNG + b"\x00" * MAX_AVATAR_SIZE, auth_headers, filename="big.png")
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"

async def test_upload_task_not_found(client, auth_headers):
    resp = await upload(client, 9999, PNG, auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TASK_NOT_FOUND"

async def test_upload_requires_token(client):
    assert (await upload(client, 1, PNG, {})).status_code == 401

async def test_get_and_delete_avatar(client, auth_headers, storage):
    task_id = await create_task(client, auth_headers)
    resp = await client.get(f"/v1/tasks/{task_id}/avatar", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "AVATAR_NOT_SET"

    await upload(client, task_id, PNG, auth_headers)
    resp = await client.get(f"/v1/tasks/{task_id}/avatar", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["key"] == f"tasks/{task_id}/avatar.png"

    assert (await client.delete(f"/v1/tasks/{task_id}/avatar", headers=auth_headers)).status_code == 204
    assert storage.objects == {}
    assert (await client.get(f"/v1/tasks/{task_id}", headers=auth_headers)).json()["avatar_key"] is None
    assert (await client.delete(f"/v1/tasks/{task_id}/avatar", headers=auth_headers)).status_code == 404

async def test_storage_down_returns_502(client, auth_headers, storage):
    task_id = await create_task(client, auth_headers)

    def broken_upload(*args, **kwargs):
        raise FileStorageError("Хранилище недоступно")

    storage.upload = broken_upload
    resp = await upload(client, task_id, PNG, auth_headers)
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "FILE_STORAGE_ERROR"

async def test_delete_task_removes_avatar(client, auth_headers, storage, make_admin):
    await make_admin("alice")
    task_id = await create_task(client, auth_headers)
    await upload(client, task_id, PNG, auth_headers)
    assert (await client.delete(f"/v1/tasks/{task_id}", headers=auth_headers)).status_code == 204
    assert storage.objects == {}


# --- Адаптер S3Storage: ошибки boto3 → ошибки предметной области ---

def client_error(code: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, operation)

def test_s3_upload_encodes_metadata():
    s3 = Mock()
    S3Storage(s3, "task-avatars").upload("k", b"data", "image/png", metadata={"Original-Filename": "котик.png"})
    params = s3.put_object.call_args.kwargs
    assert params["Bucket"] == "task-avatars"
    assert params["ContentType"] == "image/png"
    assert params["Metadata"]["original-filename"].isascii()

def test_s3_missing_object_raises_stored_file_not_found():
    s3 = Mock()
    s3.head_object.side_effect = client_error("404", "HeadObject")
    with pytest.raises(StoredFileNotFound):
        S3Storage(s3, "task-avatars").get_download_url("tasks/1/avatar.png")
    s3.generate_presigned_url.assert_not_called()

def test_s3_network_error_raises_file_storage_error():
    s3 = Mock()
    s3.put_object.side_effect = EndpointConnectionError(endpoint_url="http://localhost:9000")
    with pytest.raises(FileStorageError):
        S3Storage(s3, "task-avatars").upload("k", b"data", "image/png")
