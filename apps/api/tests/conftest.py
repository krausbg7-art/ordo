import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ordo_api.core.storage import InMemoryStorage, get_storage_dependency
from ordo_api.db import Base, get_db
from ordo_api.main import create_app


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_engine):
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    storage = InMemoryStorage()
    app.dependency_overrides[get_storage_dependency] = lambda: storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.storage = storage
        ac.job_queue = app.state.job_queue
        yield ac
