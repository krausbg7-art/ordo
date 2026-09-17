"""Определение реального типа файла по содержимому (не только по имени)."""
import io
import zipfile
from pathlib import Path

import magic

IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"}

_OOXML_MARKERS = {
    "docx": "word/document.xml",
    "xlsx": "xl/workbook.xml",
    "pptx": "ppt/presentation.xml",
}


def _sniff_ooxml(content: bytes) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        return None
    for kind, marker in _OOXML_MARKERS.items():
        if marker in names:
            return kind
    return None


def detect_kind(filename: str, content: bytes) -> str:
    """Возвращает: pdf | docx | xlsx | csv | pptx | eml | msg | ics | image | unsupported."""
    ext = Path(filename).suffix.lower().lstrip(".")
    mime = magic.from_buffer(content[:8192], mime=True)

    if mime == "application/pdf":
        return "pdf"

    if mime in ("application/zip", "application/x-zip-compressed") or mime.startswith(
        "application/vnd.openxmlformats"
    ):
        sniffed = _sniff_ooxml(content)
        if sniffed:
            return sniffed
        return "unsupported"

    if mime in ("message/rfc822",) or (ext == "eml" and mime.startswith("text/")):
        return "eml"

    if ext == "msg" and mime in (
        "application/vnd.ms-outlook",
        "application/CDFV2",
        "application/x-ole-storage",
        "application/octet-stream",
    ):
        return "msg"

    if mime == "text/calendar" or (ext == "ics" and mime.startswith("text/")):
        return "ics"

    if ext == "csv" and mime.startswith("text/"):
        return "csv"

    if mime in IMAGE_MIMES:
        return "image"

    return "unsupported"
