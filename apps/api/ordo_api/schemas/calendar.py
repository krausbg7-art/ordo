import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.calendar import CalendarKind


class CalendarAccountCreate(BaseModel):
    kind: CalendarKind
    name: str = "Календарь"
    url: str | None = None
    username: str | None = None
    password: str | None = None


class CalendarAccountUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None


class CalendarAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: CalendarKind
    name: str
    url: str | None
    username: str | None
    enabled: bool
    last_synced_at: datetime | None


class CalendarEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    uid: str
    title: str
    start_at: datetime
    end_at: datetime | None
    description: str | None
    location: str | None
