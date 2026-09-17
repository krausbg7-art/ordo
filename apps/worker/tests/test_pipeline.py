import json
import uuid

import pytest
from ordo_api.ai.base import ChatResult
from ordo_api.ai.gateway import AiGateway
from ordo_api.ai.providers import MockProvider
from ordo_api.ai.routing import RouteConfig, RoutingTable
from ordo_api.models.file import File, FileChunk, FileStatus
from ordo_api.models.task import CreatedBy, SourceType, SuggestionStatus, Task, TaskSuggestion
from sqlalchemy import select

from ordo_worker.pipeline import process_file_pipeline


class ScriptedChatProvider(MockProvider):
    """Возвращает заранее заданный ответ вместо обращения к реальной модели."""

    def __init__(self, name: str, response: dict):
        self.name = name
        self.model = f"{name}-model"
        self.response = response

    async def chat(self, messages, *, schema=None, vision=False, max_completion_tokens=None, extra=None):
        parsed = schema.model_validate(self.response) if schema else None
        return ChatResult(content=json.dumps(self.response, ensure_ascii=False), parsed=parsed, input_tokens=1, output_tokens=1)


def _routing() -> RoutingTable:
    routes = {
        name: RouteConfig(provider="qwen", fallback="kimi", max_completion_tokens=1500)
        for name in ["extract_tasks_short", "extract_tasks_long", "vision_ocr", "draft_reply", "summary"]
    }
    return RoutingTable(routes=routes)


def _gateway_with_scripted_response(response: dict) -> AiGateway:
    providers = {
        "qwen": ScriptedChatProvider("qwen", response),
        "kimi": MockProvider(),
        "qwen_vl": MockProvider(),
    }
    return AiGateway(providers, _routing(), data_residency="dev")


def _make_file(user_id: uuid.UUID, filename: str, s3_key: str) -> File:
    return File(
        id=uuid.uuid4(),
        user_id=user_id,
        filename=filename,
        content_type="application/octet-stream",
        size=1,
        s3_key=s3_key,
        status=FileStatus.processing,
    )


@pytest.mark.asyncio
async def test_pipeline_extracts_task_suggestion_from_email(db_session, storage, job_queue, fixtures_dir):
    user_id = uuid.uuid4()
    content = (fixtures_dir / "pismo.eml").read_bytes()
    storage.put("k1", content, "message/rfc822")
    file = _make_file(user_id, "pismo.eml", "k1")
    db_session.add(file)
    await db_session.flush()

    quote = "Пожалуйста, подготовьте отчёт по продажам за август до пятницы, 18 сентября."
    gateway = _gateway_with_scripted_response(
        {
            "tasks": [
                {
                    "title": "Подготовить отчёт по продажам",
                    "due_date": "2026-09-18",
                    "priority": 1,
                    "person": "Мария Сидорова",
                    "quote": quote,
                }
            ]
        }
    )

    await process_file_pipeline(db_session, gateway, storage, job_queue, file)
    await db_session.commit()

    assert file.status == FileStatus.done

    suggestions = (await db_session.execute(select(TaskSuggestion))).scalars().all()
    assert len(suggestions) == 1
    assert suggestions[0].title == "Подготовить отчёт по продажам"
    assert suggestions[0].quote == quote
    assert suggestions[0].status == SuggestionStatus.pending
    assert suggestions[0].dedup_of_task_id is None

    chunks = (await db_session.execute(select(FileChunk))).scalars().all()
    assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_pipeline_discards_candidate_with_fabricated_quote(db_session, storage, job_queue, fixtures_dir):
    user_id = uuid.uuid4()
    content = (fixtures_dir / "pismo.eml").read_bytes()
    storage.put("k2", content, "message/rfc822")
    file = _make_file(user_id, "pismo.eml", "k2")
    db_session.add(file)
    await db_session.flush()

    gateway = _gateway_with_scripted_response(
        {
            "tasks": [
                {
                    "title": "Выдуманная задача",
                    "due_date": None,
                    "priority": 2,
                    "person": None,
                    "quote": "Этой фразы точно нет в письме",
                }
            ]
        }
    )

    await process_file_pipeline(db_session, gateway, storage, job_queue, file)
    await db_session.commit()

    assert file.status == FileStatus.done
    suggestions = (await db_session.execute(select(TaskSuggestion))).scalars().all()
    assert suggestions == []


@pytest.mark.asyncio
async def test_pipeline_flags_duplicate_of_existing_task(db_session, storage, job_queue, fixtures_dir):
    user_id = uuid.uuid4()
    board_id = uuid.uuid4()
    status_id = uuid.uuid4()
    existing_task = Task(
        board_id=board_id,
        status_id=status_id,
        user_id=user_id,
        title="Подготовить отчёт по продажам",
        priority=2,
        source_type=SourceType.manual,
        created_by=CreatedBy.user,
        position=0,
    )
    db_session.add(existing_task)
    await db_session.flush()

    content = (fixtures_dir / "pismo.eml").read_bytes()
    storage.put("k3", content, "message/rfc822")
    file = _make_file(user_id, "pismo.eml", "k3")
    db_session.add(file)
    await db_session.flush()

    quote = "Пожалуйста, подготовьте отчёт по продажам за август до пятницы, 18 сентября."
    gateway = _gateway_with_scripted_response(
        {"tasks": [{"title": "Подготовить отчёт по продажам", "due_date": None, "priority": 2, "person": None, "quote": quote}]}
    )

    await process_file_pipeline(db_session, gateway, storage, job_queue, file)
    await db_session.commit()

    suggestions = (await db_session.execute(select(TaskSuggestion))).scalars().all()
    assert len(suggestions) == 1
    assert suggestions[0].dedup_of_task_id == existing_task.id


@pytest.mark.asyncio
async def test_pipeline_ics_creates_suggestions_without_ai(db_session, storage, job_queue, mock_gateway, fixtures_dir):
    user_id = uuid.uuid4()
    content = (fixtures_dir / "vstrechi.ics").read_bytes()
    storage.put("k4", content, "text/calendar")
    file = _make_file(user_id, "vstrechi.ics", "k4")
    db_session.add(file)
    await db_session.flush()

    await process_file_pipeline(db_session, mock_gateway, storage, job_queue, file)
    await db_session.commit()

    assert file.status == FileStatus.done
    suggestions = (await db_session.execute(select(TaskSuggestion))).scalars().all()
    assert len(suggestions) == 1
    assert suggestions[0].title == "Встреча с инвестором"
    assert suggestions[0].due_date.isoformat() == "2026-09-20"


@pytest.mark.asyncio
async def test_pipeline_marks_unsupported_format(db_session, storage, job_queue, mock_gateway):
    user_id = uuid.uuid4()
    storage.put("k5", b"\x00\x01garbage-not-a-real-format", "application/octet-stream")
    file = _make_file(user_id, "random.bin", "k5")
    db_session.add(file)
    await db_session.flush()

    await process_file_pipeline(db_session, mock_gateway, storage, job_queue, file)
    await db_session.commit()

    assert file.status == FileStatus.unsupported
    assert file.error


@pytest.mark.asyncio
async def test_pipeline_scanned_pdf_routes_to_vision_ocr(db_session, storage, job_queue, mock_gateway, fixtures_dir):
    user_id = uuid.uuid4()
    content = (fixtures_dir / "schet-scan.pdf").read_bytes()
    storage.put("k6", content, "application/pdf")
    file = _make_file(user_id, "schet-scan.pdf", "k6")
    db_session.add(file)
    await db_session.flush()

    await process_file_pipeline(db_session, mock_gateway, storage, job_queue, file)
    await db_session.commit()

    assert file.status == FileStatus.done
    chunks = (await db_session.execute(select(FileChunk).where(FileChunk.file_id == file.id))).scalars().all()
    assert len(chunks) >= 1
