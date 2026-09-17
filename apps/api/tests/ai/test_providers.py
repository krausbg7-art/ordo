import pytest
from pydantic import BaseModel

from ordo_api.ai.providers import MockProvider


class Suggestion(BaseModel):
    title: str
    priority: int


@pytest.mark.asyncio
async def test_mock_provider_returns_valid_schema_instance():
    provider = MockProvider()
    result = await provider.chat([{"role": "user", "content": "hi"}], schema=Suggestion)
    assert result.parsed is not None
    assert isinstance(result.parsed, Suggestion)


@pytest.mark.asyncio
async def test_mock_provider_embed_is_deterministic():
    provider = MockProvider()
    v1 = await provider.embed(["привет"])
    v2 = await provider.embed(["привет"])
    v3 = await provider.embed(["другой текст"])

    assert v1 == v2
    assert v1 != v3
    assert len(v1[0]) == MockProvider.EMBEDDING_DIM
