import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .types import GUID, EmbeddingVector

EMBEDDING_DIM = 1536


class FileStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    error = "error"
    unsupported = "unsupported"


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    filename: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(200))
    size: Mapped[int] = mapped_column(BigInteger)
    s3_key: Mapped[str] = mapped_column(String(1000))

    status: Mapped[FileStatus] = mapped_column(Enum(FileStatus), default=FileStatus.queued)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FileChunk(Base):
    __tablename__ = "file_chunks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("files.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text())
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(EMBEDDING_DIM), nullable=True)
