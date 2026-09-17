from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

ChatMessage = dict[str, Any]


@dataclass
class ChatResult:
    content: str
    parsed: BaseModel | None
    input_tokens: int | None
    output_tokens: int | None


class LLMProvider(ABC):
    """Единый интерфейс поверх OpenAI-совместимых провайдеров (Kimi, Qwen,
    собственный vLLM-сервер) и детерминированного mock-провайдера для тестов.
    """

    name: str

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        schema: type[BaseModel] | None = None,
        vision: bool = False,
        max_completion_tokens: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ChatResult: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
