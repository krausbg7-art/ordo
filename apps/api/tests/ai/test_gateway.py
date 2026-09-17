import pytest
from pydantic import BaseModel
from sqlalchemy import select

from ordo_api.ai.base import ChatResult, LLMProvider
from ordo_api.ai.gateway import AiGateway, ResidencyViolation
from ordo_api.ai.routing import RouteConfig, RoutingTable
from ordo_api.models.ai import AiCallLog


class Suggestion(BaseModel):
    title: str
    priority: int


class FakeProvider(LLMProvider):
    def __init__(self, name: str, *, fail_times: int = 0, exc: Exception | None = None):
        self.name = name
        self.model = f"{name}-model"
        self.calls = 0
        self.fail_times = fail_times
        self.exc = exc or RuntimeError("сбой провайдера")

    async def chat(self, messages, *, schema=None, vision=False, max_completion_tokens=None, extra=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.exc
        parsed = schema.model_validate({"title": self.name, "priority": 1}) if schema else None
        return ChatResult(content=self.name, parsed=parsed, input_tokens=5, output_tokens=5)

    async def embed(self, texts):
        return [[0.0, 0.0] for _ in texts]


def _routing(provider: str = "qwen", fallback: str | None = "kimi") -> RoutingTable:
    return RoutingTable(routes={"extract_tasks_short": RouteConfig(provider=provider, fallback=fallback, max_completion_tokens=100)})


@pytest.mark.asyncio
async def test_residency_ru_without_selfhost_raises():
    providers = {"qwen": FakeProvider("qwen"), "kimi": FakeProvider("kimi")}
    gateway = AiGateway(providers, _routing(), data_residency="ru")

    with pytest.raises(ResidencyViolation):
        await gateway.run("extract_tasks_short", [{"role": "user", "content": "текст письма"}], contains_user_data=True)


@pytest.mark.asyncio
async def test_residency_ru_routes_user_data_to_selfhost_only():
    providers = {"qwen": FakeProvider("qwen"), "kimi": FakeProvider("kimi"), "selfhost": FakeProvider("selfhost")}
    gateway = AiGateway(providers, _routing(), data_residency="ru")

    result = await gateway.run("extract_tasks_short", [{"role": "user", "content": "текст письма"}], contains_user_data=True)

    assert result.content == "selfhost"
    assert providers["qwen"].calls == 0
    assert providers["kimi"].calls == 0


@pytest.mark.asyncio
async def test_residency_dev_allows_cloud_provider():
    providers = {"qwen": FakeProvider("qwen"), "kimi": FakeProvider("kimi")}
    gateway = AiGateway(providers, _routing(), data_residency="dev")

    result = await gateway.run("extract_tasks_short", [{"role": "user", "content": "текст письма"}], contains_user_data=True)

    assert result.content == "qwen"


@pytest.mark.asyncio
async def test_residency_ru_does_not_restrict_requests_without_user_data():
    """Например, health-check запросы к модели без содержимого пользователя."""
    providers = {"qwen": FakeProvider("qwen"), "kimi": FakeProvider("kimi")}
    gateway = AiGateway(providers, _routing(), data_residency="ru")

    result = await gateway.run("extract_tasks_short", [{"role": "user", "content": "тест"}], contains_user_data=False)

    assert result.content == "qwen"


@pytest.mark.asyncio
async def test_falls_back_when_primary_provider_fails(db_session):
    providers = {"qwen": FakeProvider("qwen", fail_times=99), "kimi": FakeProvider("kimi")}
    gateway = AiGateway(providers, _routing(), data_residency="dev")

    result = await gateway.run(
        "extract_tasks_short", [{"role": "user", "content": "текст"}], contains_user_data=True, db=db_session
    )

    assert result.content == "kimi"

    logs = (await db_session.execute(select(AiCallLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "fallback"
    assert logs[0].provider == "kimi"


@pytest.mark.asyncio
async def test_raises_when_both_primary_and_fallback_fail(db_session):
    providers = {"qwen": FakeProvider("qwen", fail_times=99), "kimi": FakeProvider("kimi", fail_times=99)}
    gateway = AiGateway(providers, _routing(), data_residency="dev")

    with pytest.raises(RuntimeError):
        await gateway.run(
            "extract_tasks_short", [{"role": "user", "content": "текст"}], contains_user_data=True, db=db_session
        )

    logs = (await db_session.execute(select(AiCallLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "error"


@pytest.mark.asyncio
async def test_schema_validation_error_retries_same_provider_before_fallback():
    class FlakyProvider(FakeProvider):
        async def chat(self, messages, *, schema=None, vision=False, max_completion_tokens=None, extra=None):
            self.calls += 1
            if self.calls == 1:
                import json

                raise json.JSONDecodeError("bad json", "doc", 0)
            parsed = schema.model_validate({"title": self.name, "priority": 1}) if schema else None
            return ChatResult(content=self.name, parsed=parsed, input_tokens=5, output_tokens=5)

    flaky = FlakyProvider("qwen")
    providers = {"qwen": flaky, "kimi": FakeProvider("kimi")}
    gateway = AiGateway(providers, _routing(), data_residency="dev")

    result = await gateway.run(
        "extract_tasks_short", [{"role": "user", "content": "текст"}], schema=Suggestion, contains_user_data=True
    )

    assert result.content == "qwen"
    assert flaky.calls == 2
