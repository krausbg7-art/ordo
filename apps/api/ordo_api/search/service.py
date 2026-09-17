import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai.gateway import AiGateway
from ..models.calendar import CalendarAccount, CalendarEvent
from ..models.file import File, FileChunk
from ..models.search import SearchClick
from ..models.task import Task

PREFIX_MIN_LEN = 2
SEMANTIC_MIN_WORDS = 4  # «длиннее трёх слов»
SEMANTIC_SIMILARITY_THRESHOLD = 0.3
SNIPPET_RADIUS = 60

PERSON_NAMESPACE = uuid.UUID("6f6f8f2a-6f7e-4e2a-9a1a-0f7d8c9b2a10")


@dataclass
class SearchHit:
    type: str  # task | file | event | person
    id: uuid.UUID
    title: str
    subtitle: str | None
    score: float


def _recency_score(created_at: datetime) -> float:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    days = max(0.0, (datetime.now(timezone.utc) - created_at).total_seconds() / 86400)
    return 1.0 / (1.0 + days / 30)


def _click_and_time_boost(clicked_at: list[datetime]) -> float:
    if not clicked_at:
        return 0.0
    frequency_boost = math.log1p(len(clicked_at)) * 0.3

    hour_now = datetime.now(timezone.utc).hour
    close_hours = sum(1 for ts in clicked_at if min(abs(ts.hour - hour_now), 24 - abs(ts.hour - hour_now)) <= 1)
    time_of_day_boost = 0.2 * (close_hours / len(clicked_at))

    return frequency_boost + time_of_day_boost


def _match_score(text: str, query: str) -> float:
    lowered = text.lower()
    q = query.lower()
    if lowered.startswith(q):
        return 1.0
    if q in lowered:
        return 0.6
    return 0.0


def _snippet(text: str, query: str) -> str:
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[: SNIPPET_RADIUS * 2].strip()
    start = max(0, idx - SNIPPET_RADIUS)
    end = min(len(text), idx + len(query) + SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1e-9
    norm_b = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (norm_a * norm_b)


async def _click_timestamps(
    db: AsyncSession, user_id: uuid.UUID, result_type: str, ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[datetime]]:
    if not ids:
        return {}
    rows = await db.execute(
        select(SearchClick.result_id, SearchClick.created_at).where(
            SearchClick.user_id == user_id, SearchClick.result_type == result_type, SearchClick.result_id.in_(ids)
        )
    )
    stats: dict[uuid.UUID, list[datetime]] = defaultdict(list)
    for result_id, created_at in rows.all():
        stats[result_id].append(created_at)
    return stats


async def search(
    db: AsyncSession, gateway: AiGateway | None, user_id: uuid.UUID, query: str
) -> list[SearchHit]:
    query = query.strip()
    if len(query) < PREFIX_MIN_LEN:
        return []

    pattern = f"%{query}%"
    hits: list[SearchHit] = []

    # --- Задачи ---
    task_rows = (
        (
            await db.execute(
                select(Task).where(
                    Task.user_id == user_id,
                    or_(Task.title.ilike(pattern), Task.description.ilike(pattern), Task.person.ilike(pattern)),
                )
            )
        )
        .scalars()
        .all()
    )
    task_clicks = await _click_timestamps(db, user_id, "task", [t.id for t in task_rows])
    for task in task_rows:
        score = max(_match_score(task.title, query), _match_score(task.description or "", query) * 0.8)
        score += _recency_score(task.created_at) * 0.3
        score += _click_and_time_boost(task_clicks.get(task.id, []))
        hits.append(SearchHit(type="task", id=task.id, title=task.title, subtitle=task.description, score=score))

    # --- Файлы: по имени ---
    file_rows = (
        (await db.execute(select(File).where(File.user_id == user_id, File.filename.ilike(pattern)))).scalars().all()
    )
    matched_file_ids = {f.id for f in file_rows}
    file_clicks = await _click_timestamps(db, user_id, "file", list(matched_file_ids))
    for file in file_rows:
        score = _match_score(file.filename, query) + _recency_score(file.created_at) * 0.3
        score += _click_and_time_boost(file_clicks.get(file.id, []))
        hits.append(SearchHit(type="file", id=file.id, title=file.filename, subtitle=file.status.value, score=score))

    # --- Файлы: по содержимому (FileChunk) ---
    chunk_rows = (
        await db.execute(
            select(FileChunk, File)
            .join(File, File.id == FileChunk.file_id)
            .where(File.user_id == user_id, FileChunk.text.ilike(pattern))
        )
    ).all()
    seen_chunk_files: set[uuid.UUID] = set()
    for chunk, file in chunk_rows:
        if file.id in matched_file_ids or file.id in seen_chunk_files:
            continue
        seen_chunk_files.add(file.id)
        score = 0.6 + _recency_score(file.created_at) * 0.3
        hits.append(SearchHit(type="file", id=file.id, title=file.filename, subtitle=_snippet(chunk.text, query), score=score))

    # --- Смысловой поиск по эмбеддингам для длинных запросов ---
    if gateway is not None and len(query.split()) > SEMANTIC_MIN_WORDS - 1:
        already = matched_file_ids | seen_chunk_files
        try:
            query_vector = (await gateway.embed([query], contains_user_data=True))[0]
        except Exception:  # noqa: BLE001 — смысловой поиск необязателен, деградируем тихо
            query_vector = None

        if query_vector is not None:
            all_chunks = (
                await db.execute(select(FileChunk, File).join(File, File.id == FileChunk.file_id).where(File.user_id == user_id))
            ).all()
            for chunk, file in all_chunks:
                if file.id in already or chunk.embedding is None:
                    continue
                similarity = _cosine(query_vector, chunk.embedding)
                if similarity >= SEMANTIC_SIMILARITY_THRESHOLD:
                    already.add(file.id)
                    score = similarity + _recency_score(file.created_at) * 0.2
                    hits.append(
                        SearchHit(type="file", id=file.id, title=file.filename, subtitle=_snippet(chunk.text, query), score=score)
                    )

    # --- События календаря ---
    event_rows = (
        await db.execute(
            select(CalendarEvent)
            .join(CalendarAccount, CalendarAccount.id == CalendarEvent.calendar_account_id)
            .where(
                CalendarAccount.user_id == user_id,
                or_(CalendarEvent.title.ilike(pattern), CalendarEvent.description.ilike(pattern)),
            )
        )
    ).scalars().all()
    event_clicks = await _click_timestamps(db, user_id, "event", [e.id for e in event_rows])
    for event in event_rows:
        score = max(_match_score(event.title, query), _match_score(event.description or "", query) * 0.8)
        score += _recency_score(event.start_at) * 0.3
        score += _click_and_time_boost(event_clicks.get(event.id, []))
        hits.append(SearchHit(type="event", id=event.id, title=event.title, subtitle=event.description, score=score))

    # --- Люди ---
    person_rows = (
        await db.execute(
            select(Task.person)
            .where(Task.user_id == user_id, Task.person.isnot(None), Task.person.ilike(pattern))
            .distinct()
        )
    ).scalars().all()
    for name in person_rows:
        person_id = uuid.uuid5(PERSON_NAMESPACE, f"{user_id}:{name}")
        score = _match_score(name, query) + 0.1
        hits.append(SearchHit(type="person", id=person_id, title=name, subtitle="человек", score=score))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits
