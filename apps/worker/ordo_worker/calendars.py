import asyncio
from datetime import datetime, timedelta, timezone
from typing import Protocol

from ordo_api.core.ics import parse_ics_events, upsert_calendar_event
from ordo_api.models.calendar import CalendarAccount
from sqlalchemy.ext.asyncio import AsyncSession

SYNC_WINDOW_DAYS = 14


class CalDavClient(Protocol):
    def list_event_ics(self, start: datetime, end: datetime) -> list[bytes]: ...


class RealCalDavClient:
    """Обёртка над `caldav`: список календарей учётной записи и их события
    в виде отдельных .ics-документов (для парсинга общей логикой ICS)."""

    def __init__(self, url: str, username: str, password: str):
        self._url = url
        self._username = username
        self._password = password

    def list_event_ics(self, start: datetime, end: datetime) -> list[bytes]:
        import caldav

        client = caldav.DAVClient(url=self._url, username=self._username, password=self._password)
        principal = client.principal()
        results: list[bytes] = []
        for calendar in principal.calendars():
            for event in calendar.date_search(start=start, end=end):
                data = event.data
                results.append(data.encode("utf-8") if isinstance(data, str) else data)
        return results


async def sync_caldav_account(
    db: AsyncSession, account: CalendarAccount, client_factory=RealCalDavClient
) -> int:
    client: CalDavClient = client_factory(account.url, account.username, account.secret_ref or "")

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=SYNC_WINDOW_DAYS)
    ics_documents = await asyncio.to_thread(client.list_event_ics, now, end)

    count = 0
    for document in ics_documents:
        for item in parse_ics_events(document):
            await upsert_calendar_event(db, account.id, item)
            count += 1

    account.last_synced_at = now
    await db.commit()
    return count
