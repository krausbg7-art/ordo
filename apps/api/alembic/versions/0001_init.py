"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-09-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "boards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("name", sa.String(200), server_default="Моя доска"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("board_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("boards.id", ondelete="CASCADE"), index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("order", sa.Integer, server_default="0"),
        sa.Column("color", sa.String(20), server_default="#6B665D"),
    )

    source_type_enum = postgresql.ENUM("mail", "calendar", "file", "call", "note", "manual", name="sourcetype")
    created_by_enum = postgresql.ENUM("user", "ai", name="createdby")
    suggestion_status_enum = postgresql.ENUM("pending", "accepted", "rejected", name="suggestionstatus")
    file_status_enum = postgresql.ENUM("queued", "processing", "done", "error", "unsupported", name="filestatus")
    calendar_kind_enum = postgresql.ENUM("ics", "caldav", "google", name="calendarkind")

    bind = op.get_bind()
    source_type_enum.create(bind, checkfirst=True)
    created_by_enum.create(bind, checkfirst=True)
    suggestion_status_enum.create(bind, checkfirst=True)
    file_status_enum.create(bind, checkfirst=True)
    calendar_kind_enum.create(bind, checkfirst=True)

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("board_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("boards.id", ondelete="CASCADE"), index=True),
        sa.Column("status_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("statuses.id", ondelete="CASCADE"), index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer, server_default="2"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("person", sa.String(200), nullable=True),
        sa.Column("source_type", source_type_enum, server_default="manual"),
        sa.Column("source_ref", sa.String(500), nullable=True),
        sa.Column("position", sa.Integer, server_default="0"),
        sa.Column("created_by", created_by_enum, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.execute(
        "ALTER TABLE tasks ADD COLUMN title_trgm_idx_helper text GENERATED ALWAYS AS (title) STORED"
    )
    op.execute("CREATE INDEX ix_tasks_title_trgm ON tasks USING gin (title_trgm_idx_helper gin_trgm_ops)")
    op.execute(
        "CREATE INDEX ix_tasks_title_tsv ON tasks USING gin (to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(description,'')))"
    )

    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(200), nullable=False),
        sa.Column("size", sa.BigInteger, nullable=False),
        sa.Column("s3_key", sa.String(1000), nullable=False),
        sa.Column("status", file_status_enum, server_default="queued"),
        sa.Column("error", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.execute(
        "ALTER TABLE files ADD COLUMN filename_trgm_idx_helper text GENERATED ALWAYS AS (filename) STORED"
    )
    op.execute("CREATE INDEX ix_files_filename_trgm ON files USING gin (filename_trgm_idx_helper gin_trgm_ops)")

    op.create_table(
        "file_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("files.id", ondelete="CASCADE"), index=True),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float), nullable=True),
    )
    op.execute("ALTER TABLE file_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL")
    op.execute(
        "CREATE INDEX ix_file_chunks_embedding ON file_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX ix_file_chunks_text_tsv ON file_chunks USING gin (to_tsvector('russian', text))"
    )

    op.create_table(
        "task_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("files.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.Integer, server_default="2"),
        sa.Column("person", sa.String(200), nullable=True),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("status", suggestion_status_enum, server_default="pending"),
        sa.Column("dedup_of_task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "calendar_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("kind", calendar_kind_enum, nullable=False),
        sa.Column("name", sa.String(300), server_default="Календарь"),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("username", sa.String(300), nullable=True),
        sa.Column("secret_ref", sa.String(1000), nullable=True),
        sa.Column("enabled", sa.Boolean, server_default=sa.true()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "calendar_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "calendar_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calendar_accounts.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("uid", sa.String(500), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("raw", sa.Text(), nullable=True),
        sa.UniqueConstraint("calendar_account_id", "uid", name="uq_calendar_event_uid"),
    )

    op.create_table(
        "ai_call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "search_clicks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("query", sa.String(500), nullable=False),
        sa.Column("result_type", sa.String(50), nullable=False),
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("search_clicks")
    op.drop_table("ai_call_logs")
    op.drop_table("calendar_events")
    op.drop_table("calendar_accounts")
    op.drop_table("task_suggestions")
    op.drop_table("file_chunks")
    op.drop_table("files")
    op.drop_table("tasks")
    op.drop_table("statuses")
    op.drop_table("boards")
    op.drop_table("users")

    for enum_name in ("calendarkind", "filestatus", "suggestionstatus", "createdby", "sourcetype"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
