from ordo_api.core.filetype import detect_kind

from ordo_worker.extractors.docx import extract_docx_text
from ordo_worker.extractors.email_ import extract_eml
from ordo_worker.extractors.ics import parse_ics_events
from ordo_worker.extractors.pdf import extract_pdf_text
from ordo_worker.extractors.spreadsheet import extract_xlsx_text


def test_detect_kind_for_fixtures(fixtures_dir):
    assert detect_kind("pismo.eml", (fixtures_dir / "pismo.eml").read_bytes()) == "eml"
    assert detect_kind("dogovor.pdf", (fixtures_dir / "dogovor.pdf").read_bytes()) == "pdf"
    assert detect_kind("plan.xlsx", (fixtures_dir / "plan.xlsx").read_bytes()) == "xlsx"
    assert detect_kind("skan.png", (fixtures_dir / "skan.png").read_bytes()) == "image"
    assert detect_kind("vstrechi.ics", (fixtures_dir / "vstrechi.ics").read_bytes()) == "ics"
    assert detect_kind("random.bin", b"\x00\x01\x02\x03garbage") == "unsupported"


def test_extract_eml_text_and_headers(fixtures_dir):
    content = (fixtures_dir / "pismo.eml").read_bytes()
    text, attachments = extract_eml(content)

    assert "Отчёт по продажам" in text
    assert "пятницы, 18 сентября" in text
    assert attachments == []


def test_extract_pdf_with_real_text_is_not_scanned(fixtures_dir):
    content = (fixtures_dir / "dogovor.pdf").read_bytes()
    text, is_scanned = extract_pdf_text(content)

    assert is_scanned is False
    assert "ДОГОВОР ОКАЗАНИЯ УСЛУГ" in text
    assert "25 сентября 2026" in text


def test_extract_scanned_pdf_is_flagged(fixtures_dir):
    content = (fixtures_dir / "schet-scan.pdf").read_bytes()
    text, is_scanned = extract_pdf_text(content)

    assert is_scanned is True
    assert text.strip() == ""


def test_extract_xlsx_rows(fixtures_dir):
    content = (fixtures_dir / "plan.xlsx").read_bytes()
    text = extract_xlsx_text(content)

    assert "Согласовать смету" in text
    assert "Николаев" in text


def test_parse_ics_events(fixtures_dir):
    content = (fixtures_dir / "vstrechi.ics").read_bytes()
    events = parse_ics_events(content)

    assert len(events) == 1
    assert events[0]["title"] == "Встреча с инвестором"
    assert events[0]["due_date"].isoformat() == "2026-09-20"
