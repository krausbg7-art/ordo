import asyncio
import hashlib
import json
import random
from typing import Any

import openai
from pydantic import BaseModel, ValidationError

from .base import ChatMessage, ChatResult, LLMProvider

RETRYABLE_EXCEPTIONS = (
    openai.RateLimitError,
    openai.InternalServerError,
    openai.APITimeoutError,
    openai.APIConnectionError,
)


class OpenAICompatibleProvider(LLMProvider):
    """Провайдер поверх любого OpenAI-совместимого /chat/completions API:
    Moonshot (Kimi), DashScope (Qwen), либо собственный vLLM-сервер.
    """

    def __init__(
        self,
        name: str,
        *,
        base_url: str,
        api_key: str,
        model: str,
        embedding_model: str | None = None,
        supports_sampling_params: bool = True,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        request_timeout_seconds: float = 60.0,
    ):
        self.name = name
        self.model = model
        self.embedding_model = embedding_model
        self.supports_sampling_params = supports_sampling_params
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self._client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "not-needed",
            timeout=request_timeout_seconds,
        )

    async def _with_retries(self, fn):
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return await fn()
            except RETRYABLE_EXCEPTIONS as exc:
                last_exc = exc
                if attempt == self.max_retries - 1:
                    break
                delay = self.base_delay_seconds * (2**attempt) + random.uniform(0, 0.25)
                await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        schema: type[BaseModel] | None = None,
        vision: bool = False,
        max_completion_tokens: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ChatResult:
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
        if max_completion_tokens is not None:
            kwargs["max_completion_tokens"] = max_completion_tokens
        if schema is not None:
            kwargs["response_format"] = {"type": "json_object"}
        if self.supports_sampling_params and extra:
            kwargs.update(extra)

        async def call():
            return await self._client.chat.completions.create(**kwargs)

        response = await self._with_retries(call)
        choice = response.choices[0]
        content = choice.message.content or ""

        parsed: BaseModel | None = None
        if schema is not None:
            parsed = schema.model_validate(json.loads(content))

        usage = response.usage
        return ChatResult(
            content=content,
            parsed=parsed,
            input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.embedding_model:
            raise ValueError(f"У провайдера {self.name} не настроена модель эмбеддингов")

        async def call():
            return await self._client.embeddings.create(model=self.embedding_model, input=texts)

        response = await self._with_retries(call)
        return [item.embedding for item in response.data]

    async def list_models(self) -> list[str]:
        response = await self._client.models.list()
        return [m.id for m in response.data]


class MockProvider(LLMProvider):
    """Детерминированный провайдер для тестов: не обращается к сети."""

    name = "mock"
    EMBEDDING_DIM = 1536

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        schema: type[BaseModel] | None = None,
        vision: bool = False,
        max_completion_tokens: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ChatResult:
        if schema is not None:
            content = json.dumps(_mock_instance(schema), ensure_ascii=False)
            parsed = schema.model_validate_json(content)
        else:
            content = "мок-ответ"
            parsed = None
        return ChatResult(content=content, parsed=parsed, input_tokens=10, output_tokens=10)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_deterministic_vector(text, self.EMBEDDING_DIM) for text in texts]


def _deterministic_vector(text: str, dim: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for i in range(dim):
        byte = digest[i % len(digest)]
        values.append((byte / 255.0) * 2 - 1)
    return values


def _mock_instance(schema: type[BaseModel]) -> Any:
    """Строит минимально валидный экземпляр (или список из одного элемента,
    если схема — список) для тестовых сценариев без реальной модели."""
    fields = {}
    for field_name, field in schema.model_fields.items():
        annotation = field.annotation
        if annotation is str or annotation == (str | None):
            fields[field_name] = "тест"
        elif annotation is int or annotation == (int | None):
            fields[field_name] = 1
        else:
            fields[field_name] = field.default if field.default is not None else "тест"
    try:
        instance = schema(**fields)
        return instance.model_dump(mode="json")
    except ValidationError:
        return fields
