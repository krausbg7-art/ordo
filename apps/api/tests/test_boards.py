import pytest


@pytest.mark.asyncio
async def test_register_creates_default_board_with_five_statuses(client):
    payload = {"email": "board@example.com", "password": "supersecret123"}
    await client.post("/auth/register", json=payload)

    resp = await client.get("/boards")
    assert resp.status_code == 200
    boards = resp.json()
    assert len(boards) == 1
    assert len(boards[0]["statuses"]) == 5
    names = [s["name"] for s in boards[0]["statuses"]]
    assert names == ["Входящие", "В работе", "Ждёт ответа", "На согласовании", "Готово"]


@pytest.mark.asyncio
async def test_add_and_reorder_statuses(client):
    await client.post("/auth/register", json={"email": "st@example.com", "password": "supersecret123"})
    board = (await client.get("/boards")).json()[0]

    resp = await client.post(f"/boards/{board['id']}/statuses", json={"name": "Архив", "color": "#000000"})
    assert resp.status_code == 201
    new_status = resp.json()
    assert new_status["order"] == 5

    resp = await client.patch(f"/statuses/{new_status['id']}", json={"name": "Архивировано"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Архивировано"

    statuses = [s["id"] for s in board["statuses"]] + [new_status["id"]]
    reordered = list(reversed(statuses))
    payload = {"statuses": [{"id": sid, "order": i} for i, sid in enumerate(reordered)]}
    resp = await client.post(f"/boards/{board['id']}/statuses/reorder", json=payload)
    assert resp.status_code == 200
    result_ids = [s["id"] for s in resp.json()]
    assert result_ids == reordered
