from datetime import date

from pydantic import BaseModel, Field


class ExtractedTaskItem(BaseModel):
    title: str
    due_date: date | None = None
    priority: int = Field(ge=1, le=3, default=2)
    person: str | None = None
    quote: str


class ExtractedTasksResponse(BaseModel):
    tasks: list[ExtractedTaskItem] = Field(default_factory=list)
