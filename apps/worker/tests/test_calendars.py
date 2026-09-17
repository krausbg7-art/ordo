import uuid
from datetime import datetime, timezone

import pytest
from ordo_api.models.calendar import CalendarAccount, CalendarEvent, CalendarKind
from sqlalchemy import select

from ordo_worker.calendars import sync_caldav_account

ICS_EVENT_1 = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:remote-1@example.com
DTSTAMP:20260910T090000Z
DTSTART:20260918T090000Z
SUMMARY:Совет директоров
DESCRIPTION:Квартальные результаты
END:VEVENT
END:VCALENDAR
""".encode("utf-8")

ICS_EVENT_2 = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:remote-2@example.com
DTSTAMP:20260910T090000Z
DTSTART:20260919T140000Z
SUMMARY:Звонок с юристом
END:VEVENT
END:VCALENDAR
""".encode("utf-8")


class FakeCalDavClient:
    def __init__(self, url, username, password, documents=None):
        self.url = url
        self.username = username
        self.password = password
        self.documents = documents or [ICS_EVENT_1, ICS_EVENT_2]

    def list_event_ics(self, start, end):
        return self.documents


def _factory(documents=None):
    def factory(url, username, password):
        return FakeCalDavClient(url, username, password, documents)

    return factory


@pytest.mark.asyncio
async def test_sync_creates_events(db_session):
    account = CalendarAccount(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        kind=CalendarKind.caldav,
        name="Яндекс",
        url="https://caldav.yandex.ru",
        username="me",
        secret_ref="app-password",
    )
    db_session.add(account)
    await db_session.flush()

    count = await sync_caldav_account(db_session, account, client_factory=_factory())

    assert count == 2
    events = (await db_session.execute(select(CalendarEvent))).scalars().all()
    assert {e.uid for e in events} == {"remote-1@example.com", "remote-2@example.com"}
    assert account.last_synced_at is not None


@pytest.mark.asyncio
async def test_sync_is_idempotent_by_uid(db_session):
    account = CalendarAccount(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        kind=CalendarKind.caldav,
        name="Яндекс",
        url="https://caldav.yandex.ru",
        username="me",
        secret_ref="app-password",
    )
    db_session.add(account)
    await db_session.flush()

    await sync_caldav_account(db_session, account, client_factory=_factory([ICS_EVENT_1]))
    await sync_caldav_account(db_session, account, client_factory=_factory([ICS_EVENT_1]))

    events = (await db_session.execute(select(CalendarEvent))).scalars().all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_sync_updates_existing_event_fields(db_session):
    account = CalendarAccount(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        kind=CalendarKind.caldav,
        name="Яндекс",
        url="https://caldav.yandex.ru",
        username="me",
        secret_ref="app-password",
    )
    db_session.add(account)
    await db_session.flush()

    db_session.add(
        CalendarEvent(
            calendar_account_id=account.id,
            uid="remote-1@example.com",
            title="Старое название",
            start_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
    )
    await db_session.flush()

    await sync_caldav_account(db_session, account, client_factory=_factory([ICS_EVENT_1]))

    events = (await db_session.execute(select(CalendarEvent))).scalars().all()
    assert len(events) == 1
    assert events[0].title == "Совет директоров"
    assert events[0].start_at.year == 2026
