import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi import File as FastapiFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.deps import get_current_user
from ..config import get_settings
from ..core.filetype import detect_kind
from ..core.limiter import limiter
from ..core.queue import JobQueue, get_job_queue
from ..core.storage import ObjectStorage, get_storage_dependency
from ..db import get_db
from ..models.file import File, FileStatus
from ..models.user import User
from ..schemas.file import FileOut

router = APIRouter(tags=["files"])
settings = get_settings()

UNSUPPORTED_MESSAGE = "Формат файла не поддерживается"


@router.post("/files", response_model=list[FileOut], status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_files(
    request: Request,
    files: list[UploadFile] = FastapiFile(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage_dependency),
    job_queue: JobQueue = Depends(get_job_queue),
):
    created: list[File] = []
    max_size = settings.MAX_UPLOAD_MB * 1024 * 1024

    for upload in files:
        content = await upload.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Файл {upload.filename} больше {settings.MAX_UPLOAD_MB} МБ",
            )

        kind = detect_kind(upload.filename or "", content)
        file_id = uuid.uuid4()
        s3_key = f"{user.id}/{file_id}/{upload.filename}"
        storage.put(s3_key, content, upload.content_type or "application/octet-stream")

        record = File(
            id=file_id,
            user_id=user.id,
            filename=upload.filename or "без имени",
            content_type=upload.content_type or "application/octet-stream",
            size=len(content),
            s3_key=s3_key,
            status=FileStatus.unsupported if kind == "unsupported" else FileStatus.queued,
            error=UNSUPPORTED_MESSAGE if kind == "unsupported" else None,
        )
        db.add(record)
        await db.flush()
        created.append(record)

        if kind != "unsupported":
            await job_queue.enqueue_job("process_file", str(record.id))

    await db.commit()
    for record in created:
        await db.refresh(record)
    return created


@router.get("/files", response_model=list[FileOut])
async def list_files(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(File).where(File.user_id == user.id).order_by(File.created_at.desc()))
    return result.scalars().all()


@router.get("/files/{file_id}", response_model=FileOut)
async def get_file(file_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(File).where(File.id == file_id, File.user_id == user.id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")
    return record
