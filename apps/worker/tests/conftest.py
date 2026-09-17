from pathlib import Path

import pytest
import pytest_asyncio
from ordo_api.ai.gateway import AiGateway
from ordo_api.ai.providers import MockProvider
from ordo_api.ai.routing import RouteConfig, RoutingTable
from ordo_api.core.queue import InMemoryJobQueue
from ordo_api.core.storage import InMemoryStorage
from ordo_api.db import Base
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def storage():
    return InMemoryStorage()


@pytest.fixture
def job_queue():
    return InMemoryJobQueue()


def _mock_routing() -> RoutingTable:
    routes = {
        name: RouteConfig(provider="qwen", fallback="kimi", max_completion_tokens=1500)
        for name in ["extract_tasks_short", "extract_tasks_long", "vision_ocr", "draft_reply", "summary"]
    }
    return RoutingTable(routes=routes)


@pytest.fixture
def mock_gateway():
    providers = {name: MockProvider() for name in ["qwen", "kimi", "qwen_vl", "selfhost"]}
    return AiGateway(providers, _mock_routing(), data_residency="dev")


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR
