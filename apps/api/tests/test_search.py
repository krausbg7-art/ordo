import io

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from ordo_api.models.search import SearchClick


async def _register(client, email="search@example.com"):
    return await client.post("/auth/register", json={"email": email, "password": "supersecret123"})


@pytest.mark.asyncio
async def test_search_requires_at_least_two_letters(client):
    await _register(client)
    await client.post("/tasks", json={"title": "Подписать договор"})

    resp = await client.get("/search", params={"q": "П"})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


@pytest.mark.asyncio
async def test_search_finds_task_by_prefix(client):
    await _register(client, "prefix@example.com")
    await client.post("/tasks", json={"title": "Подписать договор с поставщиком"})
    await client.post("/tasks", json={"title": "Купить кофе"})

    resp = await client.get("/search", params={"q": "По"})
    results = resp.json()["results"]
    titles = [r["title"] for r in results]
    assert "Подписать договор с поставщиком" in titles
    assert "Купить кофе" not in titles
    assert results[0]["type"] == "task"


@pytest.mark.asyncio
async def test_search_finds_file_by_name(client):
    await _register(client, "files-search@example.com")
    eml_bytes = b"From: a@example.com\nTo: b@example.com\nSubject: T\n\nBody\n"
    await client.post("/files", files={"files": ("kontrakt.eml", io.BytesIO(eml_bytes), "message/rfc822")})

    resp = await client.get("/search", params={"q": "kontr"})
    results = resp.json()["results"]
    assert any(r["type"] == "file" and r["title"] == "kontrakt.eml" for r in results)


@pytest.mark.asyncio
async def test_search_finds_file_by_chunk_content(client, db_engine):
    resp = await _register(client, "content-search@example.com")
    user_id = resp.json()["id"]

    eml_bytes = b"From: a@example.com\nTo: b@example.com\nSubject: T\n\nBody\n"
    uploaded = (
        await client.post("/files", files={"files": ("doc.eml", io.BytesIO(eml_bytes), "message/rfc822")})
    ).json()[0]

    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
    from ordo_api.models.file import FileChunk

    async with session_maker() as session:
        session.add(FileChunk(file_id=uploaded["id"], chunk_index=0, text="Оплатить аренду офиса до конца месяца"))
        await session.commit()

    resp = await client.get("/search", params={"q": "аренду"})
    results = resp.json()["results"]
    assert any(r["type"] == "file" and r["id"] == uploaded["id"] for r in results)


@pytest.mark.asyncio
async def test_search_finds_event(client):
    await _register(client, "events-search@example.com")
    ics = (
        "BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:e1@x\nDTSTAMP:20260910T090000Z\n"
        "DTSTART:20260920T100000Z\nSUMMARY:Переговоры с банком\nEND:VEVENT\nEND:VCALENDAR\n"
    ).encode("utf-8")
    await client.post("/calendars/ics-import", files={"file": ("v.ics", io.BytesIO(ics), "text/calendar")})

    resp = await client.get("/search", params={"q": "Перег"})
    results = resp.json()["results"]
    assert any(r["type"] == "event" and "банком" in r["title"] for r in results)


@pytest.mark.asyncio
async def test_search_finds_person(client):
    await _register(client, "people-search@example.com")
    await client.post("/tasks", json={"title": "Проверить смету", "person": "Николаев Пётр"})

    resp = await client.get("/search", params={"q": "Никол"})
    results = resp.json()["results"]
    assert any(r["type"] == "person" and r["title"] == "Николаев Пётр" for r in results)


@pytest.mark.asyncio
async def test_search_is_isolated_per_user(client):
    await _register(client, "owner-search@example.com")
    await client.post("/tasks", json={"title": "Секретная задача"})

    await client.post("/auth/logout")
    await _register(client, "other-search@example.com")

    resp = await client.get("/search", params={"q": "Секрет"})
    assert resp.json()["results"] == []


@pytest.mark.asyncio
async def test_click_boosts_ranking(client, db_engine):
    await _register(client, "ranking@example.com")
    older = (await client.post("/tasks", json={"title": "Отчёт о продажах прошлый"})).json()
    newer = (await client.post("/tasks", json={"title": "Отчёт о продажах новый"})).json()

    # искусственно делаем "older" старше, чтобы давность не решала исход
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
    from datetime import datetime, timedelta, timezone

    from ordo_api.models.task import Task

    async with session_maker() as session:
        await session.execute(
            update(Task).where(Task.id == older["id"]).values(created_at=datetime.now(timezone.utc) - timedelta(days=200))
        )
        await session.commit()

    for _ in range(5):
        resp = await client.post(
            "/search/click", json={"query": "отчёт", "result_type": "task", "result_id": older["id"]}
        )
        assert resp.status_code == 204

    resp = await client.get("/search", params={"q": "Отчёт"})
    results = resp.json()["results"]
    task_results = [r for r in results if r["type"] == "task"]
    assert task_results[0]["id"] == older["id"]


@pytest.mark.asyncio
async def test_search_click_requires_auth(client):
    resp = await client.post(
        "/search/click", json={"query": "x", "result_type": "task", "result_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert resp.status_code == 401
