import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth.deps import get_current_user
from ..db import get_db
from ..models.board import Board, Status
from ..models.user import User
from ..schemas.board import (
    BoardCreate,
    BoardOut,
    StatusCreate,
    StatusOut,
    StatusReorderRequest,
    StatusUpdate,
)

router = APIRouter(tags=["boards"])


async def _get_owned_board(db: AsyncSession, board_id: uuid.UUID, user: User) -> Board:
    result = await db.execute(
        select(Board).options(selectinload(Board.statuses)).where(Board.id == board_id, Board.user_id == user.id)
    )
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Доска не найдена")
    return board


async def _get_owned_status(db: AsyncSession, status_id: uuid.UUID, user: User) -> Status:
    result = await db.execute(
        select(Status).join(Board, Board.id == Status.board_id).where(Status.id == status_id, Board.user_id == user.id)
    )
    st = result.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Статус не найден")
    return st


@router.get("/boards", response_model=list[BoardOut])
async def list_boards(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Board).options(selectinload(Board.statuses)).where(Board.user_id == user.id).order_by(Board.created_at)
    )
    boards = result.scalars().all()
    for b in boards:
        b.statuses.sort(key=lambda s: s.order)
    return boards


@router.post("/boards", response_model=BoardOut, status_code=status.HTTP_201_CREATED)
async def create_board(payload: BoardCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from ..models.board import DEFAULT_STATUSES

    board = Board(user_id=user.id, name=payload.name)
    db.add(board)
    await db.flush()
    for name, order, color in DEFAULT_STATUSES:
        db.add(Status(board_id=board.id, name=name, order=order, color=color))
    await db.commit()

    return await _get_owned_board(db, board.id, user)


@router.post("/boards/{board_id}/statuses", response_model=StatusOut, status_code=status.HTTP_201_CREATED)
async def create_status(
    board_id: uuid.UUID,
    payload: StatusCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await _get_owned_board(db, board_id, user)
    max_order = max((s.order for s in board.statuses), default=-1)
    st = Status(board_id=board.id, name=payload.name, color=payload.color, order=max_order + 1)
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st


@router.patch("/statuses/{status_id}", response_model=StatusOut)
async def update_status(
    status_id: uuid.UUID,
    payload: StatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    st = await _get_owned_status(db, status_id, user)
    if payload.name is not None:
        st.name = payload.name
    if payload.color is not None:
        st.color = payload.color
    await db.commit()
    await db.refresh(st)
    return st


@router.post("/boards/{board_id}/statuses/reorder", response_model=list[StatusOut])
async def reorder_statuses(
    board_id: uuid.UUID,
    payload: StatusReorderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await _get_owned_board(db, board_id, user)
    by_id = {s.id: s for s in board.statuses}
    for item in payload.statuses:
        st = by_id.get(item.id)
        if not st:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Статус не принадлежит доске")
        st.order = item.order
    await db.commit()

    result = await db.execute(select(Status).where(Status.board_id == board_id).order_by(Status.order))
    return result.scalars().all()
