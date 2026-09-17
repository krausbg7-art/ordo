import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .types import GUID


class CalendarKind(str, enum.Enum):
    ics = "ics"
    caldav = "caldav"
    google = "google"


class CalendarAccount(Base):
    __tablename__ = "calendar_accounts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    kind: Mapped[CalendarKind] = mapped_column(Enum(CalendarKind))
    name: Mapped[str] = mapped_column(String(300), default="Календарь")
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    username: Mapped[str | None] = mapped_column(String(300), nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # ссылка на секрет, не сам пароль
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (UniqueConstraint("calendar_account_id", "uid", name="uq_calendar_event_uid"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    calendar_account_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("calendar_accounts.id", ondelete="CASCADE"), index=True
    )
    uid: Mapped[str] = mapped_column(String(500), index=True)

    title: Mapped[str] = mapped_column(String(500))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw: Mapped[str | None] = mapped_column(Text(), nullable=True)
