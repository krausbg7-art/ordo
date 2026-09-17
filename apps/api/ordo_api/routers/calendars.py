import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.deps import get_current_user
from ..config import get_settings
from ..core.ics import parse_ics_events, upsert_calendar_event
from ..core.queue import JobQueue, get_job_queue
from ..db import get_db
from ..models.board import Board, Status
from ..models.calendar import CalendarAccount, CalendarEvent, CalendarKind
from ..models.task import SourceType, Task
from ..models.user import User
from ..schemas.calendar import (
    CalendarAccountCreate,
    CalendarAccountOut,
    CalendarAccountUpdate,
    CalendarEventOut,
)
from ..schemas.task import TaskOut

router = APIRouter(tags=["calendars"])
settings = get_settings()

ICS_IMPORT_ACCOUNT_NAME = "Импортированные файлы"


async def _get_owned_account(db: AsyncSession, account_id: uuid.UUID, user: User) -> CalendarAccount:
    result = await db.execute(select(CalendarAccount).where(CalendarAccount.id == account_id, CalendarAccount.user_id == user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Календарь не найден")
    return account


async def _get_or_create_ics_account(db: AsyncSession, user: User) -> CalendarAccount:
    result = await db.execute(
        select(CalendarAccount).where(
            CalendarAccount.user_id == user.id,
            CalendarAccount.kind == CalendarKind.ics,
            CalendarAccount.name == ICS_IMPORT_ACCOUNT_NAME,
        )
    )
    account = result.scalar_one_or_none()
    if account:
        return account

    account = CalendarAccount(user_id=user.id, kind=CalendarKind.ics, name=ICS_IMPORT_ACCOUNT_NAME)
    db.add(account)
    await db.flush()
    return account


@router.get("/calendars", response_model=list[CalendarAccountOut])
async def list_calendars(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CalendarAccount).where(CalendarAccount.user_id == user.id))
    return result.scalars().all()


@router.post("/calendars", response_model=CalendarAccountOut, status_code=status.HTTP_201_CREATED)
async def create_calendar(
    payload: CalendarAccountCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if payload.kind == CalendarKind.google and not settings.GOOGLE_CALENDAR_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Google Calendar отключён (фиче-флаг)")

    if payload.kind == CalendarKind.caldav and not (payload.url and payload.username and payload.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Для CalDAV нужны url, username и пароль приложения"
        )

    account = CalendarAccount(
        user_id=user.id,
        kind=payload.kind,
        name=payload.name,
        url=payload.url,
        username=payload.username,
        secret_ref=payload.password,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.patch("/calendars/{account_id}", response_model=CalendarAccountOut)
async def update_calendar(
    account_id: uuid.UUID,
    payload: CalendarAccountUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_owned_account(db, account_id, user)
    if payload.name is not None:
        account.name = payload.name
    if payload.enabled is not None:
        account.enabled = payload.enabled
    await db.commit()
    await db.refresh(account)
    return account


@router.post("/calendars/ics-import", response_model=list[CalendarEventOut])
async def import_ics_file(
    file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    try:
        items = parse_ics_events(content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Не удалось разобрать .ics: {exc}") from exc

    account = await _get_or_create_ics_account(db, user)
    for item in items:
        await upsert_calendar_event(db, account.id, item)
    account.last_synced_at = datetime.now(timezone.utc)
    await db.commit()

    result = await db.execute(select(CalendarEvent).where(CalendarEvent.calendar_account_id == account.id))
    return result.scalars().all()


@router.post("/calendars/{account_id}/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_calendar(
    account_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    job_queue: JobQueue = Depends(get_job_queue),
):
    account = await _get_owned_account(db, account_id, user)
    if account.kind != CalendarKind.caldav:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Синхронизация доступна только для CalDAV")
    await job_queue.enqueue_job("sync_calendar_account", str(account.id))
    return {"status": "queued"}


@router.get("/calendars/{account_id}/events", response_model=list[CalendarEventOut])
async def list_events(
    account_id: uuid.UUID,
    from_date: date | None = None,
    to_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_account(db, account_id, user)
    stmt = select(CalendarEvent).where(CalendarEvent.calendar_account_id == account_id)
    if from_date is not None:
        stmt = stmt.where(CalendarEvent.start_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
    if to_date is not None:
        stmt = stmt.where(CalendarEvent.start_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))
    stmt = stmt.order_by(CalendarEvent.start_at)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/calendars/{account_id}/events/add-all", response_model=list[TaskOut])
async def add_all_events_as_tasks(
    account_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _get_owned_account(db, account_id, user)
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.calendar_account_id == account_id))
    events = result.scalars().all()

    created = []
    for event in events:
        created.append(await _event_to_task(db, user, event))
    await db.commit()
    for task in created:
        await db.refresh(task)
    return created


@router.post("/calendar-events/{event_id}/to-task", response_model=TaskOut)
async def event_to_task(event_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CalendarEvent)
        .join(CalendarAccount, CalendarAccount.id == CalendarEvent.calendar_account_id)
        .where(CalendarEvent.id == event_id, CalendarAccount.user_id == user.id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Событие не найдено")

    task = await _event_to_task(db, user, event)
    await db.commit()
    await db.refresh(task)
    return task


async def _event_to_task(db: AsyncSession, user: User, event: CalendarEvent) -> Task:
    existing = await db.execute(
        select(Task).where(
            Task.user_id == user.id, Task.source_type == SourceType.calendar, Task.source_ref == str(event.id)
        )
    )
    already = existing.scalar_one_or_none()
    if already:
        return already

    board_result = await db.execute(select(Board).where(Board.user_id == user.id).order_by(Board.created_at))
    board = board_result.scalars().first()
    if not board:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="У пользователя нет доски")
    inbox_result = await db.execute(select(Status).where(Status.board_id == board.id).order_by(Status.order))
    inbox = inbox_result.scalars().first()

    position_result = await db.execute(select(Task).where(Task.status_id == inbox.id).order_by(Task.position.desc()))
    last_task = position_result.scalars().first()

    task = Task(
        board_id=board.id,
        status_id=inbox.id,
        user_id=user.id,
        title=event.title,
        description=event.description,
        priority=2,
        due_date=event.start_at.date(),
        source_type=SourceType.calendar,
        source_ref=str(event.id),
        position=(last_task.position + 1) if last_task else 0,
        created_by="ai",
    )
    db.add(task)
    await db.flush()
    return task


@router.post("/calendars/google/connect")
async def connect_google_calendar(user: User = Depends(get_current_user)):
    if not settings.GOOGLE_CALENDAR_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Google Calendar отключён (фиче-флаг)")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth для Google Calendar — TODO следующего этапа",
    )
