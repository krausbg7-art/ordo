import uuid

import structlog
from ordo_api.ai.deps import get_ai_gateway
from ordo_api.core.queue import ArqJobQueue
from ordo_api.core.storage import get_storage
from ordo_api.db import async_session_maker
from ordo_api.models.calendar import CalendarAccount, CalendarKind
from ordo_api.models.file import File, FileStatus
from sqlalchemy import select

from .calendars import sync_caldav_account
from .pipeline import process_file_pipeline

logger = structlog.get_logger(__name__)


async def process_file(ctx, file_id: str) -> None:
    async with async_session_maker() as db:
        result = await db.execute(select(File).where(File.id == uuid.UUID(file_id)))
        file = result.scalar_one_or_none()
        if file is None:
            logger.warning("process_file.not_found", file_id=file_id)
            return

        file.status = FileStatus.processing
        await db.commit()

        gateway = get_ai_gateway()
        storage = get_storage()
        job_queue = ArqJobQueue(ctx["redis"])

        try:
            await process_file_pipeline(db, gateway, storage, job_queue, file)
            await db.commit()
            logger.info("process_file.done", file_id=file_id, status=file.status.value)
        except Exception as exc:  # noqa: BLE001 — файл должен получить понятный статус ошибки
            await db.rollback()
            file.status = FileStatus.error
            file.error = str(exc)[:1000]
            await db.commit()
            logger.error("process_file.failed", file_id=file_id, error=str(exc))


async def sync_calendar_account(ctx, account_id: str) -> None:
    async with async_session_maker() as db:
        result = await db.execute(select(CalendarAccount).where(CalendarAccount.id == uuid.UUID(account_id)))
        account = result.scalar_one_or_none()
        if account is None or not account.enabled or account.kind != CalendarKind.caldav:
            return

        try:
            count = await sync_caldav_account(db, account)
            logger.info("sync_calendar_account.done", account_id=account_id, events=count)
        except Exception as exc:  # noqa: BLE001 — ошибка синхронизации не должна ронять воркер
            await db.rollback()
            logger.error("sync_calendar_account.failed", account_id=account_id, error=str(exc))


async def sync_all_caldav_accounts(ctx) -> None:
    """Раз в 15 минут синхронизирует все включённые CalDAV-аккаунты."""
    async with async_session_maker() as db:
        result = await db.execute(
            select(CalendarAccount.id).where(CalendarAccount.kind == CalendarKind.caldav, CalendarAccount.enabled.is_(True))
        )
        account_ids = [str(row) for row in result.scalars().all()]

    for account_id in account_ids:
        await sync_calendar_account(ctx, account_id)
