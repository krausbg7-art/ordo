import base64
import uuid

from ordo_api.ai.gateway import AiGateway

OCR_PROMPT = "Распознай весь текст на изображении дословно, без пояснений и комментариев."


async def ocr_image(gateway: AiGateway, content: bytes, user_id: uuid.UUID, mime: str = "image/png") -> str:
    b64 = base64.b64encode(content).decode("ascii")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": OCR_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }
    ]
    result = await gateway.run("vision_ocr", messages, vision=True, contains_user_data=True, user_id=user_id)
    return result.content


def convert_heic_to_png(content: bytes) -> bytes | None:
    try:
        from io import BytesIO

        import pillow_heif
        from PIL import Image

        pillow_heif.register_heif_opener()
        image = Image.open(BytesIO(content))
        buf = BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:  # noqa: BLE001 — HEIC не декодировался, файл будет помечен неподдерживаемым
        return None
