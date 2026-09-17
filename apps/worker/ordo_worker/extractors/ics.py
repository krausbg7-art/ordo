from datetime import date, datetime

from icalendar import Calendar


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
