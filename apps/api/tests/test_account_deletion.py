import io

import pytest
from sqlalchemy import select

from ordo_api.models.ai import AiCallLog
from ordo_api.models.board import Board
from ordo_api.models.file import File, FileChunk
from ordo_api.models.task import Task, TaskSuggestion
from ordo_api.models.user import User


@pytest.mark.asyncio
async def test_delete_account_removes_everything(client, db_engine):
    resp = await client.post("/auth/register", json={"email": "delete@example.com", "password": "supersecret123"})
    user_id = resp.json()["id"]

    await client.post("/tasks", json={"title": "Задача"})
    eml_bytes = b"From: a@example.com\nTo: b@example.com\nSubject: T\n\nBody\n"
    uploaded = (await client.post("/files", files={"files": ("d.eml", io.BytesIO(eml_bytes), "message/rfc822")})).json()[0]

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_maker() as session:
        session.add(FileChunk(file_id=uploaded["id"], chunk_index=0, text="некоторый текст"))
        session.add(AiCallLog(user_id=user_id, provider="mock", model="m", task_type="extract_tasks_short", duration_ms=1, status="ok"))
        await session.commit()

    resp = await client.delete("/auth/me")
    assert resp.status_code == 204

    async with session_maker() as session:
        assert (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none() is None
        assert (await session.execute(select(Board).where(Board.user_id == user_id))).scalars().all() == []
        assert (await session.execute(select(Task).where(Task.user_id == user_id))).scalars().all() == []
        assert (await session.execute(select(File).where(File.user_id == user_id))).scalars().all() == []
        assert (await session.execute(select(FileChunk))).scalars().all() == []
        assert (await session.execute(select(AiCallLog).where(AiCallLog.user_id == user_id))).scalars().all() == []
        assert (await session.execute(select(TaskSuggestion).where(TaskSuggestion.user_id == user_id))).scalars().all() == []

    assert client.storage._data == {}

    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_requires_auth(client):
    resp = await client.delete("/auth/me")
    assert resp.status_code == 401
