import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.deps import get_current_user
from ..db import get_db
from ..models.board import Board, Status
from ..models.task import SourceType, Task
from ..models.user import User
from ..schemas.task import TaskCreate, TaskMove, TaskOut, TaskUpdate

router = APIRouter(tags=["tasks"])


async def _default_board(db: AsyncSession, user: User) -> Board:
    result = await db.execute(select(Board).where(Board.user_id == user.id).order_by(Board.created_at))
    board = result.scalars().first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="У пользователя нет доски")
    return board


async def _get_owned_task(db: AsyncSession, task_id: uuid.UUID, user: User) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return task


async def _get_owned_status(db: AsyncSession, status_id: uuid.UUID, user: User) -> Status:
    result = await db.execute(
        select(Status).join(Board, Board.id == Status.board_id).where(Status.id == status_id, Board.user_id == user.id)
    )
    st = result.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Статус не найден")
    return st


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    board_id: uuid.UUID | None = None,
    status_id: uuid.UUID | None = None,
    source_type: SourceType | None = None,
    priority: int | None = Query(default=None, ge=1, le=3),
    due_before: date | None = None,
    due_after: date | None = None,
    person: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if board_id is None:
        board = await _default_board(db, user)
        board_id = board.id

    stmt = select(Task).where(Task.user_id == user.id, Task.board_id == board_id)
    if status_id is not None:
        stmt = stmt.where(Task.status_id == status_id)
    if source_type is not None:
        stmt = stmt.where(Task.source_type == source_type)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if due_before is not None:
        stmt = stmt.where(Task.due_date <= due_before)
    if due_after is not None:
        stmt = stmt.where(Task.due_date >= due_after)
    if person is not None:
        stmt = stmt.where(Task.person == person)

    stmt = stmt.order_by(Task.status_id, Task.position)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.board_id is not None:
        board_result = await db.execute(select(Board).where(Board.id == payload.board_id, Board.user_id == user.id))
        board = board_result.scalar_one_or_none()
        if not board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Доска не найдена")
    else:
        board = await _default_board(db, user)

    if payload.status_id is not None:
        st = await _get_owned_status(db, payload.status_id, user)
    else:
        status_result = await db.execute(select(Status).where(Status.board_id == board.id).order_by(Status.order))
        st = status_result.scalars().first()
        if not st:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="На доске нет статусов")

    max_position_result = await db.execute(select(Task).where(Task.status_id == st.id).order_by(Task.position.desc()))
    last_task = max_position_result.scalars().first()
    next_position = (last_task.position + 1) if last_task else 0

    task = Task(
        board_id=board.id,
        status_id=st.id,
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        person=payload.person,
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        position=next_position,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID, payload: TaskUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    task = await _get_owned_task(db, task_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = await _get_owned_task(db, task_id, user)
    await db.delete(task)
    await db.commit()


@router.post("/tasks/{task_id}/move", response_model=TaskOut)
async def move_task(
    task_id: uuid.UUID, payload: TaskMove, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Перемещает карточку между колонками/позициями одной транзакцией:
    задачи в целевом статусе переупорядочиваются, включая саму карточку."""
    task = await _get_owned_task(db, task_id, user)
    target_status = await _get_owned_status(db, payload.status_id, user)

    result = await db.execute(
        select(Task)
        .where(Task.status_id == target_status.id, Task.id != task.id)
        .order_by(Task.position)
    )
    siblings = list(result.scalars().all())

    insert_at = max(0, min(payload.position, len(siblings)))
    siblings.insert(insert_at, task)

    task.status_id = target_status.id
    for index, sibling in enumerate(siblings):
        sibling.position = index

    await db.commit()
    await db.refresh(task)
    return task
