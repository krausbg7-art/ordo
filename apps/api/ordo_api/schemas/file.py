import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.file import FileStatus


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    size: int
    status: FileStatus
    error: str | None
    created_at: datetime
