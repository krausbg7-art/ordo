import json
import time

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models.ai import AiCallLog
from .base import ChatMessage, ChatResult, LLMProvider
from .providers import MockProvider, OpenAICompatibleProvider
from .routing import RouteConfig, RoutingTable


class ResidencyViolation(Exception):
    """Запрос с пользовательскими данными пытается уйти к облачному
    провайдеру, когда DATA_RESIDENCY=ru разрешает только selfhost."""


def build_providers(settings: Settings) -> dict[str, LLMProvider]:
    providers: dict[str, LLMProvider] = {
        "kimi": OpenAICompatibleProvider(
            "kimi",
            base_url=settings.MOONSHOT_BASE_URL,
            api_key=settings.MOONSHOT_API_KEY,
            model=settings.KIMI_MODEL,
            supports_sampling_params=False,
        ),
        "qwen": OpenAICompatibleProvider(
            "qwen",
            base_url=settings.DASHSCOPE_BASE_URL,
            api_key=settings.DASHSCOPE_API_KEY,
            model=settings.QWEN_MODEL,
            embedding_model="text-embedding-v3",
        ),
        "qwen_vl": OpenAICompatibleProvider(
            "qwen_vl",
            base_url=settings.DASHSCOPE_BASE_URL,
            api_key=settings.DASHSCOPE_API_KEY,
            model=settings.QWEN_VL_MODEL,
        ),
        "mock": MockProvider(),
    }
    if settings.SELFHOST_BASE_URL:
        providers["selfhost"] = OpenAICompatibleProvider(
            "selfhost",
            base_url=settings.SELFHOST_BASE_URL,
            api_key="",
            model=settings.SELFHOST_MODEL,
            embedding_model=settings.SELFHOST_MODEL,
        )
    return providers


class AiGateway:
    def __init__(self, providers: dict[str, LLMProvider], routing: RoutingTable, data_residency: str):
        self.providers = providers
        self.routing = routing
        self.data_residency = data_residency

    def _select_names(self, route: RouteConfig, contains_user_data: bool) -> tuple[str, str | None]:
        if contains_user_data and self.data_residency == "ru":
            if "selfhost" not in self.providers:
                raise ResidencyViolation(
                    "DATA_RESIDENCY=ru требует настроенного SELFHOST_BASE_URL для запросов "
                    "с пользовательскими данными; облачные kimi/qwen запрещены"
                )
            return "selfhost", None
        return route.provider, route.fallback

    async def run(
        self,
        task_type: str,
        messages: list[ChatMessage],
        *,
        schema: type[BaseModel] | None = None,
        vision: bool = False,
        contains_user_data: bool = True,
        db: AsyncSession | None = None,
        user_id=None,
    ) -> ChatResult:
        route = self.routing.resolve(task_type)
        provider_name, fallback_name = self._select_names(route, contains_user_data)

        start = time.monotonic()
        status = "ok"
        used_provider_name = provider_name
        result: ChatResult | None = None
        error: Exception | None = None

        try:
            result = await self._call_with_schema_retry(
                self.providers[provider_name], messages, schema, vision, route.max_completion_tokens
            )
        except Exception as primary_exc:  # noqa: BLE001 — намеренно широкий перехват для fallback
            if fallback_name and fallback_name in self.providers:
                try:
                    result = await self._call_with_schema_retry(
                        self.providers[fallback_name], messages, schema, vision, route.max_completion_tokens
                    )
                    status = "fallback"
                    used_provider_name = fallback_name
                except Exception as fallback_exc:  # noqa: BLE001
                    status = "error"
                    error = fallback_exc
            else:
                status = "error"
                error = primary_exc

        duration_ms = int((time.monotonic() - start) * 1000)

        if db is not None:
            used_provider = self.providers.get(used_provider_name)
            db.add(
                AiCallLog(
                    user_id=user_id,
                    provider=used_provider_name,
                    model=getattr(used_provider, "model", used_provider_name),
                    task_type=task_type,
                    input_tokens=result.input_tokens if result else None,
                    output_tokens=result.output_tokens if result else None,
                    duration_ms=duration_ms,
                    status=status,
                )
            )
            await db.commit()

        if error is not None:
            raise error
        assert result is not None
        return result

    async def _call_with_schema_retry(
        self,
        provider: LLMProvider,
        messages: list[ChatMessage],
        schema: type[BaseModel] | None,
        vision: bool,
        max_completion_tokens: int,
    ) -> ChatResult:
        try:
            return await provider.chat(messages, schema=schema, vision=vision, max_completion_tokens=max_completion_tokens)
        except (ValidationError, json.JSONDecodeError) as exc:
            retry_messages = [
                *messages,
                {
                    "role": "user",
                    "content": f"Ответ не прошёл проверку схемы: {exc}. Верни исправленный строгий JSON без пояснений.",
                },
            ]
            return await provider.chat(
                retry_messages, schema=schema, vision=vision, max_completion_tokens=max_completion_tokens
            )
