import uuid

from ordo_api.models.task import CreatedBy, SourceType, Task

from ordo_worker.extraction.dedup import find_similar_task


def _task(title: str) -> Task:
    return Task(
        id=uuid.uuid4(),
        board_id=uuid.uuid4(),
        status_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title=title,
        priority=2,
        source_type=SourceType.manual,
        created_by=CreatedBy.user,
        position=0,
    )


def test_finds_near_duplicate_by_title():
    existing = [_task("Подготовить отчёт по продажам за август")]
    match = find_similar_task("Подготовить отчёт по продажам за август", existing)
    assert match is existing[0]


def test_does_not_match_unrelated_titles():
    existing = [_task("Купить кофе для офиса")]
    match = find_similar_task("Подписать договор с поставщиком", existing)
    assert match is None


def test_empty_existing_tasks_returns_none():
    assert find_similar_task("Что угодно", []) is None
