import enum
import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .types import GUID


class SourceType(str, enum.Enum):
    mail = "mail"
    calendar = "calendar"
    file = "file"
    call = "call"
    note = "note"
    manual = "manual"


class CreatedBy(str, enum.Enum):
    user = "user"
    ai = "ai"


class SuggestionStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    status_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("statuses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1..3
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    person: Mapped[str | None] = mapped_column(String(200), nullable=True)

    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), default=SourceType.manual)
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[CreatedBy] = mapped_column(Enum(CreatedBy), default=CreatedBy.user)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaskSuggestion(Base):
    __tablename__ = "task_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("files.id", ondelete="CASCADE"), nullable=True)

    title: Mapped[str] = mapped_column(String(500))
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quote: Mapped[str] = mapped_column(Text())

    status: Mapped[SuggestionStatus] = mapped_column(Enum(SuggestionStatus), default=SuggestionStatus.pending)
    dedup_of_task_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("tasks.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
