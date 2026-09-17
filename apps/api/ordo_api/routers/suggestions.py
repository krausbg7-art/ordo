import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.deps import get_current_user
from ..db import get_db
from ..models.board import Board, Status
from ..models.task import SourceType, SuggestionStatus, Task, TaskSuggestion
from ..models.user import User
from ..schemas.suggestion import TaskSuggestionOut
from ..schemas.task import TaskOut

router = APIRouter(tags=["suggestions"])


async def _get_owned_suggestion(db: AsyncSession, suggestion_id: uuid.UUID, user: User) -> TaskSuggestion:
    result = await db.execute(
        select(TaskSuggestion).where(TaskSuggestion.id == suggestion_id, TaskSuggestion.user_id == user.id)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Предложение не найдено")
    return suggestion


@router.get("/suggestions", response_model=list[TaskSuggestionOut])
async def list_suggestions(
    status_filter: SuggestionStatus = SuggestionStatus.pending,
    file_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TaskSuggestion).where(TaskSuggestion.user_id == user.id, TaskSuggestion.status == status_filter)
    if file_id is not None:
        stmt = stmt.where(TaskSuggestion.file_id == file_id)
    stmt = stmt.order_by(TaskSuggestion.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/suggestions/{suggestion_id}/accept", response_model=TaskOut)
async def accept_suggestion(
    suggestion_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    suggestion = await _get_owned_suggestion(db, suggestion_id, user)
    if suggestion.status != SuggestionStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Предложение уже обработано")

    board_result = await db.execute(select(Board).where(Board.user_id == user.id).order_by(Board.created_at))
    board = board_result.scalars().first()
    if not board:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="У пользователя нет доски")

    inbox_result = await db.execute(select(Status).where(Status.board_id == board.id).order_by(Status.order))
    inbox = inbox_result.scalars().first()
    if not inbox:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="На доске нет статусов")

    position_result = await db.execute(select(Task).where(Task.status_id == inbox.id).order_by(Task.position.desc()))
    last_task = position_result.scalars().first()

    task = Task(
        board_id=board.id,
        status_id=inbox.id,
        user_id=user.id,
        title=suggestion.title,
        description=suggestion.quote,
        priority=suggestion.priority,
        due_date=suggestion.due_date,
        person=suggestion.person,
        source_type=SourceType.file,
        source_ref=str(suggestion.file_id) if suggestion.file_id else None,
        position=(last_task.position + 1) if last_task else 0,
        created_by="ai",
    )
    db.add(task)
    suggestion.status = SuggestionStatus.accepted
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/suggestions/{suggestion_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_suggestion(
    suggestion_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    suggestion = await _get_owned_suggestion(db, suggestion_id, user)
    if suggestion.status != SuggestionStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Предложение уже обработано")
    suggestion.status = SuggestionStatus.rejected
    await db.commit()
