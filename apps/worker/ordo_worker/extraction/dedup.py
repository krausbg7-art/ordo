import difflib

from ordo_api.models.task import Task

SIMILARITY_THRESHOLD = 0.82


def find_similar_task(candidate_title: str, existing_tasks: list[Task]) -> Task | None:
    """Помечает предложение как «возможно, уже есть» по схожести названия."""
    normalized_candidate = candidate_title.strip().lower()
    best_task: Task | None = None
    best_ratio = 0.0

    for task in existing_tasks:
        ratio = difflib.SequenceMatcher(None, normalized_candidate, task.title.strip().lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_task = task

    if best_task is not None and best_ratio >= SIMILARITY_THRESHOLD:
        return best_task
    return None
