
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.ai import AiCallLog
from ..models.board import Board, Status
from ..models.calendar import CalendarAccount, CalendarEvent
from ..models.file import File, FileChunk
from ..models.search import SearchClick
from ..models.task import Task, TaskSuggestion
from ..models.user import User
from .storage import ObjectStorage


async def delete_user_account(db: AsyncSession, storage: ObjectStorage, user: User) -> None:
    """Полное и необратимое удаление аккаунта: файлы из хранилища,
    фрагменты, задачи, предложения, календари, логи ИИ и клики поиска."""
    files_result = await db.execute(select(File).where(File.user_id == user.id))
    files = files_result.scalars().all()
    for file in files:
        try:
            storage.delete(file.s3_key)
        except Exception:  # noqa: BLE001 — отсутствие объекта в хранилище не должно блокировать удаление
            pass

    file_ids = [f.id for f in files]
    board_ids_result = await db.execute(select(Board.id).where(Board.user_id == user.id))
    board_ids = list(board_ids_result.scalars().all())
    calendar_account_ids_result = await db.execute(select(CalendarAccount.id).where(CalendarAccount.user_id == user.id))
    calendar_account_ids = list(calendar_account_ids_result.scalars().all())

    if file_ids:
        await db.execute(delete(FileChunk).where(FileChunk.file_id.in_(file_ids)))
    await db.execute(delete(TaskSuggestion).where(TaskSuggestion.user_id == user.id))
    await db.execute(delete(AiCallLog).where(AiCallLog.user_id == user.id))
    await db.execute(delete(SearchClick).where(SearchClick.user_id == user.id))
    if calendar_account_ids:
        await db.execute(delete(CalendarEvent).where(CalendarEvent.calendar_account_id.in_(calendar_account_ids)))
    await db.execute(delete(CalendarAccount).where(CalendarAccount.user_id == user.id))
    await db.execute(delete(Task).where(Task.user_id == user.id))
    if board_ids:
        await db.execute(delete(Status).where(Status.board_id.in_(board_ids)))
    await db.execute(delete(Board).where(Board.user_id == user.id))
    await db.execute(delete(File).where(File.user_id == user.id))
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()
