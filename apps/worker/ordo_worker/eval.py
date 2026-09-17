"""`make eval` — прогоняет фикстуры из tests/fixtures/ через реальную
модель (если заданы ключи ИИ) и печатает точность извлечения задач.

Запуск: cd apps/worker && python -m ordo_worker.eval
"""
import asyncio
import sys
from datetime import date
from pathlib import Path

from ordo_api.ai.deps import get_ai_gateway
from ordo_api.config import get_settings

from .extraction.extract import extract_tasks_from_text
from .extractors.email_ import extract_eml
from .extractors.pdf import extract_pdf_text
from .extractors.spreadsheet import extract_xlsx_text

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"

CASES = [
    {
        "name": "pismo.eml",
        "loader": lambda content: extract_eml(content)[0],
        "expected_keywords": ["отчёт", "продаж"],
    },
    {
        "name": "dogovor.pdf",
        "loader": lambda content: extract_pdf_text(content)[0],
        "expected_keywords": ["акт"],
    },
    {
        "name": "plan.xlsx",
        "loader": lambda content: extract_xlsx_text(content),
        "expected_keywords": ["смету"],
    },
]


async def main() -> int:
    settings = get_settings()

    if settings.DATA_RESIDENCY == "ru" and not settings.SELFHOST_BASE_URL:
        print(
            "DATA_RESIDENCY=ru и SELFHOST_BASE_URL не задан — по правилам резидентности "
            "eval не может отправлять содержимое фикстур в облачные kimi/qwen. "
            "Задайте DATA_RESIDENCY=dev для тестового прогона или настройте собственный vLLM."
        )
        return 0

    if not (settings.MOONSHOT_API_KEY or settings.DASHSCOPE_API_KEY or settings.SELFHOST_BASE_URL):
        print("Ключи ИИ не заданы в .env (MOONSHOT_API_KEY/DASHSCOPE_API_KEY/SELFHOST_BASE_URL) — eval пропущен.")
        return 0

    gateway = get_ai_gateway()
    total = 0
    hits = 0

    for case in CASES:
        path = FIXTURES_DIR / case["name"]
        content = path.read_bytes()
        text = case["loader"](content)

        candidates = await extract_tasks_from_text(gateway, text, today=date(2026, 9, 17))
        total += 1
        found = any(
            all(keyword.lower() in f"{c.title} {c.quote}".lower() for keyword in case["expected_keywords"])
            for c in candidates
        )
        hits += int(found)
        print(f"[{'OK' if found else 'MISS'}] {case['name']}: найдено кандидатов — {len(candidates)}")

    accuracy = hits / total if total else 0.0
    print(f"\nТочность извлечения: {hits}/{total} = {accuracy:.0%}")
    return 0 if accuracy == 1.0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
