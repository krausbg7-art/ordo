from datetime import date, datetime, timezone

from icalendar import Calendar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models


def parse_ics_events(content: bytes) -> list[dict]:
    calendar = Calendar.from_ical(content)
    events = []
    for component in calendar.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("summary", "") or "")
        description = str(component.get("description", "") or "")
        uid = str(component.get("uid", "") or "")

        dtstart = component.get("dtstart")
        due_date: date | None = None
        if dtstart is not None:
            value = dtstart.dt
            due_date = value.date() if isinstance(value, datetime) else value

        events.append({"uid": uid, "title": summary, "description": description, "due_date": due_date})
    return events


async def upsert_calendar_event(db: AsyncSession, account_id, item: dict) -> None:
    """Создаёт или обновляет CalendarEvent по (account_id, uid) — повторный
    импорт того же события не создаёт дубликат."""
    if not item["uid"]:
        return

    existing = await db.execute(
        select(models.CalendarEvent).where(
            models.CalendarEvent.calendar_account_id == account_id, models.CalendarEvent.uid == item["uid"]
        )
    )
    event = existing.scalar_one_or_none()

    start_at = item["due_date"]
    if start_at is not None and not isinstance(start_at, datetime):
        start_at = datetime.combine(start_at, datetime.min.time(), tzinfo=timezone.utc)

    if event is None:
        db.add(
            models.CalendarEvent(
                calendar_account_id=account_id,
                uid=item["uid"],
                title=item["title"] or "Событие",
                start_at=start_at or datetime.now(timezone.utc),
                description=item["description"],
            )
        )
    else:
        event.title = item["title"] or event.title
        event.start_at = start_at or event.start_at
        event.description = item["description"]
