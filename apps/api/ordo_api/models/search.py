import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .types import GUID


class SearchClick(Base):
    __tablename__ = "search_clicks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    query: Mapped[str] = mapped_column(String(500))
    result_type: Mapped[str] = mapped_column(String(50))  # task | file | event | person
    result_id: Mapped[uuid.UUID] = mapped_column(GUID())

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
