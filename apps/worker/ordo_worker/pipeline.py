import uuid
from datetime import date

from ordo_api.ai.gateway import AiGateway
from ordo_api.core.filetype import detect_kind
from ordo_api.core.queue import JobQueue
from ordo_api.core.storage import ObjectStorage
from ordo_api.models.file import File, FileChunk, FileStatus
from ordo_api.models.task import Task, TaskSuggestion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .chunking import split_into_chunks
from .extraction.dedup import find_similar_task
from .extraction.extract import extract_tasks_from_text
from .extractors.docx import extract_docx_text
from .extractors.email_ import extract_eml, extract_msg
from .extractors.ics import parse_ics_events
from .extractors.image import convert_heic_to_png, ocr_image
from .extractors.pdf import extract_pdf_text, pdf_pages_to_images
from .extractors.pptx import extract_pptx_text
from .extractors.spreadsheet import extract_csv_text, extract_xlsx_text

UNSUPPORTED_MESSAGE = "Формат файла не поддерживается"


async def _extract_text_and_attachments(
    gateway: AiGateway, kind: str, filename: str, content: bytes, user_id: uuid.UUID
) -> tuple[str | None, list[tuple[str, bytes]]]:
    if kind == "pdf":
        text, is_scanned = extract_pdf_text(content)
        if is_scanned:
            page_images = pdf_pages_to_images(content)
            ocr_parts = [await ocr_image(gateway, img, user_id) for img in page_images]
            text = "\n\n".join(part for part in ocr_parts if part)
        return text, []

    if kind == "docx":
        return extract_docx_text(content), []

    if kind == "xlsx":
        return extract_xlsx_text(content), []

    if kind == "csv":
        return extract_csv_text(content), []

    if kind == "pptx":
        return extract_pptx_text(content), []

    if kind == "eml":
        return extract_eml(content)

    if kind == "msg":
        return extract_msg(content)

    if kind == "image":
        image_bytes = content
        if filename.lower().endswith((".heic", ".heif")):
            converted = convert_heic_to_png(content)
            if converted is None:
                return None, []
            image_bytes = converted
        text = await ocr_image(gateway, image_bytes, user_id)
        return text, []

    return None, []


async def process_file_pipeline(
    db: AsyncSession,
    gateway: AiGateway,
    storage: ObjectStorage,
    job_queue: JobQueue,
    file: File,
) -> None:
    content = storage.get(file.s3_key)
    kind = detect_kind(file.filename, content)

    if kind == "ics":
        events = parse_ics_events(content)
        for event in events:
            title = event["title"] or "Событие из календаря"
            db.add(
                TaskSuggestion(
                    user_id=file.user_id,
                    file_id=file.id,
                    title=title,
                    due_date=event["due_date"],
                    priority=2,
                    person=None,
                    quote=event["description"] or title,
                )
            )
        file.status = FileStatus.done
        return

    if kind == "unsupported":
        file.status = FileStatus.unsupported
        file.error = UNSUPPORTED_MESSAGE
        return

    text, attachments = await _extract_text_and_attachments(gateway, kind, file.filename, content, file.user_id)

    if text is None:
        file.status = FileStatus.unsupported
        file.error = UNSUPPORTED_MESSAGE
        return

    chunks = split_into_chunks(text)
    if chunks:
        vectors = await gateway.embed(chunks, contains_user_data=True)
        for index, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            db.add(FileChunk(file_id=file.id, chunk_index=index, text=chunk_text, embedding=vector))

    candidates = await extract_tasks_from_text(gateway, text, today=date.today(), db=db, user_id=file.user_id)

    existing_tasks_result = await db.execute(select(Task).where(Task.user_id == file.user_id))
    existing_tasks = list(existing_tasks_result.scalars().all())

    for candidate in candidates:
        duplicate = find_similar_task(candidate.title, existing_tasks)
        db.add(
            TaskSuggestion(
                user_id=file.user_id,
                file_id=file.id,
                title=candidate.title,
                due_date=candidate.due_date,
                priority=candidate.priority,
                person=candidate.person,
                quote=candidate.quote,
                dedup_of_task_id=duplicate.id if duplicate else None,
            )
        )

    for attachment_name, attachment_content in attachments:
        attachment_kind = detect_kind(attachment_name, attachment_content)
        if attachment_kind == "unsupported":
            continue
        attachment_id = uuid.uuid4()
        key = f"{file.user_id}/{attachment_id}/{attachment_name}"
        storage.put(key, attachment_content, "application/octet-stream")
        attachment_file = File(
            id=attachment_id,
            user_id=file.user_id,
            filename=attachment_name,
            content_type="application/octet-stream",
            size=len(attachment_content),
            s3_key=key,
            status=FileStatus.queued,
        )
        db.add(attachment_file)
        await db.flush()
        await job_queue.enqueue_job("process_file", str(attachment_id))

    file.status = FileStatus.done
