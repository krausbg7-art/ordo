import io

import pytest


async def _register(client, email="files@example.com"):
    await client.post("/auth/register", json={"email": email, "password": "supersecret123"})


@pytest.mark.asyncio
async def test_upload_supported_file_is_queued_and_enqueued(client):
    await _register(client)

    eml_bytes = (
        b"From: a@example.com\nTo: b@example.com\nSubject: Test\n"
        b"Content-Type: text/plain; charset=utf-8\n\nHello\n"
    )
    files = {"files": ("letter.eml", io.BytesIO(eml_bytes), "message/rfc822")}

    resp = await client.post("/files", files=files)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "queued"
    assert body[0]["filename"] == "letter.eml"
    assert client.job_queue.jobs == [("process_file", (body[0]["id"],))]


@pytest.mark.asyncio
async def test_upload_unsupported_file_marks_status(client):
    await _register(client, "unsupported@example.com")

    files = {"files": ("weird.xyz", io.BytesIO(b"\x00\x01\x02not-a-real-format"), "application/octet-stream")}
    resp = await client.post("/files", files=files)
    assert resp.status_code == 201
    body = resp.json()
    assert body[0]["status"] == "unsupported"
    assert body[0]["error"]
    assert client.job_queue.jobs == []


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(client):
    await _register(client, "big@example.com")

    from ordo_api.config import get_settings

    settings = get_settings()
    too_big = b"0" * (settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    files = {"files": ("big.bin", io.BytesIO(too_big), "application/octet-stream")}

    resp = await client.post("/files", files=files)
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_list_and_get_file(client):
    await _register(client, "list@example.com")
    eml_bytes = b"From: a@example.com\nTo: b@example.com\nSubject: T\n\nBody\n"
    files = {"files": ("l.eml", io.BytesIO(eml_bytes), "message/rfc822")}
    uploaded = (await client.post("/files", files=files)).json()[0]

    resp = await client.get("/files")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/files/{uploaded['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == uploaded["id"]


@pytest.mark.asyncio
async def test_files_are_isolated_per_user(client):
    await _register(client, "owner@example.com")
    eml_bytes = b"From: a@example.com\nTo: b@example.com\nSubject: T\n\nBody\n"
    files = {"files": ("o.eml", io.BytesIO(eml_bytes), "message/rfc822")}
    await client.post("/files", files=files)

    await client.post("/auth/logout")
    await _register(client, "other@example.com")

    resp = await client.get("/files")
    assert resp.json() == []
