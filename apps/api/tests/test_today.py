from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from ordo_api.models.task import Task


@pytest.mark.asyncio
async def test_today_prioritizes_overdue_then_priority(client):
    await client.post("/auth/register", json={"email": "today@example.com", "password": "supersecret123"})

    overdue = (
        await client.post(
            "/tasks", json={"title": "Просрочено", "due_date": str(date.today() - timedelta(days=3))}
        )
    ).json()
    high_priority = (await client.post("/tasks", json={"title": "Важное", "priority": 1})).json()
    low_priority = (await client.post("/tasks", json={"title": "Неважное", "priority": 3})).json()

    resp = await client.get("/today")
    assert resp.status_code == 200
    items = resp.json()

    assert items[0]["task"]["id"] == overdue["id"]
    assert items[0]["reason"] == "Просрочена"
    assert items[1]["task"]["id"] == high_priority["id"]
    assert len(items) <= 3


@pytest.mark.asyncio
async def test_today_excludes_done_tasks(client):
    await client.post("/auth/register", json={"email": "today2@example.com", "password": "supersecret123"})
    board = (await client.get("/boards")).json()[0]
    done_status = next(s for s in board["statuses"] if s["name"] == "Готово")

    await client.post("/tasks", json={"title": "Завершено", "status_id": done_status["id"], "priority": 1})
    resp = await client.get("/today")
    assert resp.json() == []


@pytest.mark.asyncio
async def test_today_flags_long_waiting_tasks(client, db_engine):
    await client.post("/auth/register", json={"email": "today3@example.com", "password": "supersecret123"})
    board = (await client.get("/boards")).json()[0]
    waiting_status = next(s for s in board["statuses"] if s["name"] == "Ждёт ответа")

    task = (
        await client.post(
            "/tasks", json={"title": "Ждёт клиента", "status_id": waiting_status["id"], "priority": 3}
        )
    ).json()

    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_maker() as session:
        stale = datetime.now(timezone.utc) - timedelta(days=5)
        await session.execute(update(Task).where(Task.id == task["id"]).values(updated_at=stale))
        await session.commit()

    resp = await client.get("/today")
    items = resp.json()
    assert items[0]["task"]["id"] == task["id"]
    assert items[0]["reason"] == "Ждёт ответа больше двух дней"
