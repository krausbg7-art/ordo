import io

import pytest

ICS_CONTENT = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Ordo//Tests//RU
BEGIN:VEVENT
UID:event-1@ordo.example
DTSTAMP:20260910T090000Z
DTSTART:20260920T100000Z
DTEND:20260920T110000Z
SUMMARY:Встреча с инвестором
DESCRIPTION:Обсудить условия раунда
END:VEVENT
END:VCALENDAR
""".encode("utf-8")


async def _register(client, email="cal@example.com"):
    await client.post("/auth/register", json={"email": email, "password": "supersecret123"})


@pytest.mark.asyncio
async def test_ics_import_creates_events(client):
    await _register(client)

    resp = await client.post("/calendars/ics-import", files={"file": ("v.ics", io.BytesIO(ICS_CONTENT), "text/calendar")})
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 1
    assert events[0]["title"] == "Встреча с инвестором"
    assert events[0]["uid"] == "event-1@ordo.example"


@pytest.mark.asyncio
async def test_ics_reimport_does_not_duplicate(client):
    await _register(client, "reimport@example.com")

    files = {"file": ("v.ics", io.BytesIO(ICS_CONTENT), "text/calendar")}
    await client.post("/calendars/ics-import", files=files)
    files = {"file": ("v.ics", io.BytesIO(ICS_CONTENT), "text/calendar")}
    resp = await client.post("/calendars/ics-import", files=files)

    assert len(resp.json()) == 1

    calendars = (await client.get("/calendars")).json()
    assert len(calendars) == 1  # повторный импорт переиспользует тот же календарь


@pytest.mark.asyncio
async def test_event_to_task_creates_task_in_inbox(client):
    await _register(client, "totask@example.com")
    events = (
        await client.post("/calendars/ics-import", files={"file": ("v.ics", io.BytesIO(ICS_CONTENT), "text/calendar")})
    ).json()
    event_id = events[0]["id"]

    resp = await client.post(f"/calendar-events/{event_id}/to-task")
    assert resp.status_code == 200
    task = resp.json()
    assert task["title"] == "Встреча с инвестором"
    assert task["source_type"] == "calendar"

    # повторный вызов не создаёт вторую задачу
    resp2 = await client.post(f"/calendar-events/{event_id}/to-task")
    assert resp2.json()["id"] == task["id"]

    resp3 = await client.get("/tasks")
    assert len(resp3.json()) == 1


@pytest.mark.asyncio
async def test_add_all_events_as_tasks(client):
    await _register(client, "addall@example.com")
    account_events = (
        await client.post("/calendars/ics-import", files={"file": ("v.ics", io.BytesIO(ICS_CONTENT), "text/calendar")})
    ).json()

    calendars = (await client.get("/calendars")).json()
    account_id = calendars[0]["id"]

    resp = await client.post(f"/calendars/{account_id}/events/add-all")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    tasks = (await client.get("/tasks")).json()
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_create_caldav_account_requires_credentials(client):
    await _register(client, "caldav@example.com")

    resp = await client.post("/calendars", json={"kind": "caldav", "name": "Яндекс"})
    assert resp.status_code == 400

    resp = await client.post(
        "/calendars",
        json={"kind": "caldav", "name": "Яндекс", "url": "https://caldav.yandex.ru", "username": "me", "password": "app-pass"},
    )
    assert resp.status_code == 201
    account = resp.json()
    assert account["kind"] == "caldav"
    assert "password" not in account


@pytest.mark.asyncio
async def test_sync_caldav_enqueues_job(client):
    await _register(client, "sync@example.com")
    account = (
        await client.post(
            "/calendars",
            json={
                "kind": "caldav",
                "name": "iCloud",
                "url": "https://caldav.icloud.com",
                "username": "me",
                "password": "app-pass",
            },
        )
    ).json()

    resp = await client.post(f"/calendars/{account['id']}/sync")
    assert resp.status_code == 202
    assert client.job_queue.jobs == [("sync_calendar_account", (account["id"],))]


@pytest.mark.asyncio
async def test_google_calendar_disabled_by_default(client):
    await _register(client, "google@example.com")

    resp = await client.post("/calendars", json={"kind": "google", "name": "Google"})
    assert resp.status_code == 404

    resp = await client.post("/calendars/google/connect")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_calendar_toggle_enabled(client):
    await _register(client, "toggle@example.com")
    account = (
        await client.post(
            "/calendars",
            json={"kind": "caldav", "name": "X", "url": "https://x", "username": "u", "password": "p"},
        )
    ).json()

    resp = await client.patch(f"/calendars/{account['id']}", json={"enabled": False, "name": "Отключённый"})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
    assert resp.json()["name"] == "Отключённый"
