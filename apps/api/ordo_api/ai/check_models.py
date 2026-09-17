"""Проверяет, что модели, заданные в .env, ещё существуют у провайдеров.

Запуск: python -m ordo_api.ai.check_models
"""
import asyncio
import sys

from ..config import get_settings
from .gateway import build_providers
from .providers import OpenAICompatibleProvider

CHECKS = [
    ("kimi", "KIMI_MODEL"),
    ("qwen", "QWEN_MODEL"),
    ("qwen_vl", "QWEN_VL_MODEL"),
    ("selfhost", "SELFHOST_MODEL"),
]


async def main() -> int:
    settings = get_settings()
    providers = build_providers(settings)
    exit_code = 0

    for provider_name, model_attr in CHECKS:
        provider = providers.get(provider_name)
        configured_model = getattr(settings, model_attr)

        if provider is None or not isinstance(provider, OpenAICompatibleProvider):
            print(f"[{provider_name}] пропущено: провайдер не настроен")
            continue
        if not configured_model:
            print(f"[{provider_name}] пропущено: модель не задана в .env ({model_attr})")
            continue

        try:
            available = await provider.list_models()
        except Exception as exc:  # noqa: BLE001
            print(f"[{provider_name}] не удалось получить список моделей: {exc}")
            exit_code = 1
            continue

        if configured_model in available:
            print(f"[{provider_name}] OK: {configured_model}")
        else:
            print(
                f"[{provider_name}] ВНИМАНИЕ: модель '{configured_model}' не найдена в списке "
                f"провайдера. Доступно: {', '.join(available[:10])}{'…' if len(available) > 10 else ''}"
            )
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
