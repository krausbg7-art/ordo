import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from ordo_api.models.task import TaskSuggestion


async def _insert_suggestion(db_engine, user_id, **overrides):
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_maker() as session:
        suggestion = TaskSuggestion(
            user_id=user_id,
            title=overrides.get("title", "Подписать акт"),
            due_date=overrides.get("due_date"),
            priority=overrides.get("priority", 2),
            person=overrides.get("person"),
            quote=overrides.get("quote", "цитата из документа"),
        )
        session.add(suggestion)
        await session.commit()
        await session.refresh(suggestion)
        return suggestion.id


@pytest.mark.asyncio
async def test_list_pending_suggestions(client, db_engine):
    resp = await client.post("/auth/register", json={"email": "sug@example.com", "password": "supersecret123"})
    user_id = resp.json()["id"]

    await _insert_suggestion(db_engine, user_id)

    resp = await client.get("/suggestions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_accept_suggestion_creates_task_in_inbox(client, db_engine):
    resp = await client.post("/auth/register", json={"email": "accept@example.com", "password": "supersecret123"})
    user_id = resp.json()["id"]
    suggestion_id = await _insert_suggestion(db_engine, user_id, title="Оплатить счёт", priority=1)

    resp = await client.post(f"/suggestions/{suggestion_id}/accept")
    assert resp.status_code == 200
    task = resp.json()
    assert task["title"] == "Оплатить счёт"
    assert task["source_type"] == "file"
    assert task["priority"] == 1

    board = (await client.get("/boards")).json()[0]
    inbox_id = board["statuses"][0]["id"]
    assert task["status_id"] == inbox_id

    resp = await client.get("/suggestions")
    assert resp.json() == []

    resp = await client.post(f"/suggestions/{suggestion_id}/accept")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reject_suggestion(client, db_engine):
    resp = await client.post("/auth/register", json={"email": "reject@example.com", "password": "supersecret123"})
    user_id = resp.json()["id"]
    suggestion_id = await _insert_suggestion(db_engine, user_id)

    resp = await client.post(f"/suggestions/{suggestion_id}/reject")
    assert resp.status_code == 204

    resp = await client.get("/suggestions")
    assert resp.json() == []
