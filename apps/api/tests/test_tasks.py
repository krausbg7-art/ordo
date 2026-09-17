import pytest


async def _register_and_get_board(client, email="tasks@example.com"):
    await client.post("/auth/register", json={"email": email, "password": "supersecret123"})
    board = (await client.get("/boards")).json()[0]
    return board


@pytest.mark.asyncio
async def test_create_and_list_tasks(client):
    board = await _register_and_get_board(client)
    inbox = board["statuses"][0]

    resp = await client.post("/tasks", json={"title": "Подписать договор", "priority": 1})
    assert resp.status_code == 201
    task = resp.json()
    assert task["status_id"] == inbox["id"]
    assert task["position"] == 0

    resp = await client.get("/tasks")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Подписать договор"


@pytest.mark.asyncio
async def test_update_and_delete_task(client):
    await _register_and_get_board(client, "update@example.com")
    task = (await client.post("/tasks", json={"title": "Черновик"})).json()

    resp = await client.patch(f"/tasks/{task['id']}", json={"title": "Готовый черновик", "priority": 1})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Готовый черновик"
    assert resp.json()["priority"] == 1

    resp = await client.delete(f"/tasks/{task['id']}")
    assert resp.status_code == 204

    resp = await client.get("/tasks")
    assert resp.json() == []


@pytest.mark.asyncio
async def test_move_task_reorders_transactionally(client):
    board = await _register_and_get_board(client, "move@example.com")
    inbox, in_progress = board["statuses"][0], board["statuses"][1]

    await client.post("/tasks", json={"title": "A"})
    t2 = (await client.post("/tasks", json={"title": "B"})).json()
    await client.post("/tasks", json={"title": "C", "status_id": in_progress["id"]})

    resp = await client.post(f"/tasks/{t2['id']}/move", json={"status_id": in_progress["id"], "position": 0})
    assert resp.status_code == 200
    moved = resp.json()
    assert moved["status_id"] == in_progress["id"]
    assert moved["position"] == 0

    resp = await client.get("/tasks", params={"status_id": in_progress["id"]})
    ordered = resp.json()
    assert [t["title"] for t in ordered] == ["B", "C"]
    assert [t["position"] for t in ordered] == [0, 1]

    resp = await client.get("/tasks", params={"status_id": inbox["id"]})
    remaining = resp.json()
    assert [t["title"] for t in remaining] == ["A"]


@pytest.mark.asyncio
async def test_filter_tasks_by_priority_and_source(client):
    await _register_and_get_board(client, "filter@example.com")

    await client.post("/tasks", json={"title": "Низкий приоритет", "priority": 3})
    await client.post("/tasks", json={"title": "Высокий приоритет", "priority": 1})

    resp = await client.get("/tasks", params={"priority": 1})
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Высокий приоритет"
