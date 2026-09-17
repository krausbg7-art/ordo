import uuid

from pydantic import BaseModel


class SearchResultOut(BaseModel):
    type: str
    id: uuid.UUID
    title: str
    subtitle: str | None
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultOut]


class SearchClickRequest(BaseModel):
    query: str
    result_type: str
    result_id: uuid.UUID
