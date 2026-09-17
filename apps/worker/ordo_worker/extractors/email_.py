import email
import tempfile
from email import policy


def extract_eml(content: bytes) -> tuple[str, list[tuple[str, bytes]]]:
    msg = email.message_from_bytes(content, policy=policy.default)
    headers = (
        f"От: {msg.get('From', '')}\n"
        f"Кому: {msg.get('To', '')}\n"
        f"Тема: {msg.get('Subject', '')}\n"
        f"Дата: {msg.get('Date', '')}\n\n"
    )

    body = ""
    attachments: list[tuple[str, bytes]] = []

    if msg.is_multipart():
        for part in msg.walk():
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                payload = part.get_payload(decode=True) or b""
                attachments.append((part.get_filename() or "вложение", payload))
            elif part.get_content_type() == "text/plain" and not body:
                try:
                    body = part.get_content()
                except Exception:  # noqa: BLE001
                    body = ""
    else:
        try:
            body = msg.get_content()
        except Exception:  # noqa: BLE001
            body = ""

    return headers + body, attachments


def extract_msg(content: bytes) -> tuple[str, list[tuple[str, bytes]]]:
    import extract_msg as extract_msg_lib

    with tempfile.NamedTemporaryFile(suffix=".msg") as tmp:
        tmp.write(content)
        tmp.flush()
        message = extract_msg_lib.Message(tmp.name)
        headers = (
            f"От: {message.sender or ''}\n"
            f"Кому: {message.to or ''}\n"
            f"Тема: {message.subject or ''}\n"
            f"Дата: {message.date or ''}\n\n"
        )
        body = message.body or ""
        attachments = [
            (att.longFilename or att.shortFilename or "вложение", att.data)
            for att in message.attachments
            if att.data
        ]
        message.close()

    return headers + body, attachments
