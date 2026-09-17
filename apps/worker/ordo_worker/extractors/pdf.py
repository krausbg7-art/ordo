from io import BytesIO

import pdfplumber

MIN_CHARS_PER_PAGE = 40


def extract_pdf_text(content: bytes) -> tuple[str, bool]:
    """Возвращает (текст, признак_скана). Скан — почти без извлекаемого текста."""
    pages_text: list[str] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            pages_text.append(page.extract_text() or "")

    text = "\n".join(pages_text)
    avg_chars = len(text.strip()) / max(1, len(pages_text))
    is_scanned = avg_chars < MIN_CHARS_PER_PAGE
    return text, is_scanned


def pdf_pages_to_images(content: bytes) -> list[bytes]:
    from pdf2image import convert_from_bytes

    images = convert_from_bytes(content, fmt="png")
    output = []
    for image in images:
        buf = BytesIO()
        image.save(buf, format="PNG")
        output.append(buf.getvalue())
    return output
