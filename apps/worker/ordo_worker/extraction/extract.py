import uuid
from datetime import date

from ordo_api.ai.gateway import AiGateway
from sqlalchemy.ext.asyncio import AsyncSession

from .prompt import build_extract_tasks_messages
from .schemas import ExtractedTaskItem, ExtractedTasksResponse

LONG_INPUT_THRESHOLD_CHARS = 30_000


async def extract_tasks_from_text(
    gateway: AiGateway,
    text: str,
    *,
    today: date | None = None,
    db: AsyncSession | None = None,
    user_id: uuid.UUID | None = None,
) -> list[ExtractedTaskItem]:
    text = text.strip()
    if not text:
        return []

    today = today or date.today()
    task_type = "extract_tasks_long" if len(text) > LONG_INPUT_THRESHOLD_CHARS else "extract_tasks_short"
    messages = build_extract_tasks_messages(text, today)

    result = await gateway.run(
        task_type,
        messages,
        schema=ExtractedTasksResponse,
        contains_user_data=True,
        db=db,
        user_id=user_id,
    )

    parsed = result.parsed
    if parsed is None:
        return []

    # Защита от выдумок: quote должен быть дословным фрагментом исходного текста.
    return [candidate for candidate in parsed.tasks if candidate.quote and candidate.quote in text]
