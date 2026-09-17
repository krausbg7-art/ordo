import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.task import CreatedBy, SourceType


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    board_id: uuid.UUID
    status_id: uuid.UUID
    title: str
    description: str | None
    priority: int
    due_date: date | None
    person: str | None
    source_type: SourceType
    source_ref: str | None
    position: int
    created_by: CreatedBy
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    board_id: uuid.UUID | None = None
    status_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: int = Field(default=2, ge=1, le=3)
    due_date: date | None = None
    person: str | None = None
    source_type: SourceType = SourceType.manual
    source_ref: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    priority: int | None = Field(default=None, ge=1, le=3)
    due_date: date | None = None
    person: str | None = None


class TaskMove(BaseModel):
    status_id: uuid.UUID
    position: int = Field(ge=0)


class TodayTask(BaseModel):
    task: TaskOut
    reason: str
