"""search: доп. trgm-индексы для мгновенного поиска

Revision ID: 0002_search_indexes
Revises: 0001_init
Create Date: 2026-09-17

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_search_indexes"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_tasks_description_trgm ON tasks USING gin (description gin_trgm_ops)")
    op.execute("CREATE INDEX ix_tasks_person_trgm ON tasks USING gin (person gin_trgm_ops)")
    op.execute("CREATE INDEX ix_file_chunks_text_trgm ON file_chunks USING gin (text gin_trgm_ops)")
    op.execute("CREATE INDEX ix_calendar_events_title_trgm ON calendar_events USING gin (title gin_trgm_ops)")
    op.execute(
        "CREATE INDEX ix_calendar_events_description_trgm ON calendar_events USING gin (description gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_calendar_events_description_trgm")
    op.execute("DROP INDEX IF EXISTS ix_calendar_events_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_file_chunks_text_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tasks_person_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tasks_description_trgm")
