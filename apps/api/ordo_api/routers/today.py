from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.deps import get_current_user
from ..db import get_db
from ..models.board import Board, Status
from ..models.task import Task
from ..models.user import User
from ..schemas.task import TodayTask

router = APIRouter(tags=["today"])

WAITING_STATUS_NAME = "Ждёт ответа"
DONE_STATUS_NAME = "Готово"
WAITING_THRESHOLD_DAYS = 2


def _reason(task: Task, status_name: str, today: date) -> tuple[tuple[int, int, int, date], str]:
    is_urgent_due = task.due_date is not None and task.due_date <= today + timedelta(days=1)

    is_waiting_too_long = False
    if status_name == WAITING_STATUS_NAME:
        updated = task.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        is_waiting_too_long = (datetime.now(timezone.utc) - updated).days > WAITING_THRESHOLD_DAYS

    rank0 = 0 if is_urgent_due else 1
    rank1 = task.priority
    rank2 = 0 if is_waiting_too_long else 1
    sort_key = (rank0, rank1, rank2, task.due_date or date.max)

    if is_urgent_due:
        if task.due_date < today:
            reason = "Просрочена"
        elif task.due_date == today:
            reason = "Срок сегодня"
        else:
            reason = "Срок завтра"
    elif is_waiting_too_long:
        reason = "Ждёт ответа больше двух дней"
    else:
        reason = f"Приоритет {task.priority} из 3"

    return sort_key, reason


@router.get("/today", response_model=list[TodayTask])
async def today(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    board_result = await db.execute(select(Board).where(Board.user_id == user.id).order_by(Board.created_at))
    board = board_result.scalars().first()
    if not board:
        return []

    statuses_result = await db.execute(select(Status).where(Status.board_id == board.id))
    statuses_by_id = {s.id: s.name for s in statuses_result.scalars().all()}

    tasks_result = await db.execute(select(Task).where(Task.user_id == user.id, Task.board_id == board.id))
    tasks = [t for t in tasks_result.scalars().all() if statuses_by_id.get(t.status_id) != DONE_STATUS_NAME]

    today_date = date.today()
    scored = [
        (_reason(t, statuses_by_id.get(t.status_id, ""), today_date), t)
        for t in tasks
    ]
    scored.sort(key=lambda pair: pair[0][0])

    return [TodayTask(task=t, reason=reason) for (_, reason), t in scored[:3]]
