import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from ..models.task import SuggestionStatus


class TaskSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_id: uuid.UUID | None
    title: str
    due_date: date | None
    priority: int
    person: str | None
    quote: str
    status: SuggestionStatus
    dedup_of_task_id: uuid.UUID | None
    created_at: datetime
