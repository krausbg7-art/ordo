import pytest


@pytest.mark.asyncio
async def test_register_login_me(client):
    payload = {"email": "boss@example.com", "password": "supersecret123"}

    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    assert resp.json()["email"] == payload["email"]
    assert "ordo_session" in resp.cookies

    resp = await client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == payload["email"]

    resp = await client.post("/auth/logout")
    assert resp.status_code == 204

    resp = await client.get("/auth/me")
    assert resp.status_code == 401

    resp = await client.post("/auth/login", json=payload)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "password": "supersecret123"}
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201

    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client):
    payload = {"email": "wrong@example.com", "password": "supersecret123"}
    await client.post("/auth/register", json=payload)

    resp = await client.post("/auth/login", json={"email": payload["email"], "password": "nope"})
    assert resp.status_code == 401
