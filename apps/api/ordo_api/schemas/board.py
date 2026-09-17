import uuid

from pydantic import BaseModel, ConfigDict, Field


class StatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    order: int
    color: str


class StatusCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    color: str = "#6B665D"


class StatusUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    color: str | None = None


class StatusReorderItem(BaseModel):
    id: uuid.UUID
    order: int


class StatusReorderRequest(BaseModel):
    statuses: list[StatusReorderItem]


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    statuses: list[StatusOut]


class BoardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200, default="Новая доска")
