from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.deps import get_current_user
from ..auth.security import create_access_token, hash_password, verify_password
from ..config import get_settings
from ..core.account import delete_user_account
from ..core.storage import ObjectStorage, get_storage_dependency
from ..db import get_db
from ..models.board import DEFAULT_STATUSES, Board, Status
from ..models.user import User
from ..schemas.auth import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_session_cookie(response: Response, user_id) -> None:
    token = create_access_token(user_id)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.JWT_TTL_SECONDS,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Пользователь уже существует")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    await db.flush()

    board = Board(user_id=user.id, name="Моя доска")
    db.add(board)
    await db.flush()

    for name, order, color in DEFAULT_STATUSES:
        db.add(Status(board_id=board.id, name=name, order=order, color=color))

    await db.commit()
    await db.refresh(user)

    _set_session_cookie(response, user.id)
    return user


@router.post("/login", response_model=UserOut)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

    _set_session_cookie(response, user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(settings.COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage_dependency),
):
    await delete_user_account(db, storage, user)
    response.delete_cookie(settings.COOKIE_NAME, path="/")
