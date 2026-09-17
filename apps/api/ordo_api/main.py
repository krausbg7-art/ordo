from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .core.limiter import limiter
from .core.logging import configure_logging, get_logger
from .core.queue import InMemoryJobQueue, create_arq_job_queue
from .routers import auth, boards, calendars, files, health, search, suggestions, tasks, today

settings = get_settings()
configure_logging(settings.ENV)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ordo_api.startup", env=settings.ENV)
    try:
        app.state.job_queue = await create_arq_job_queue(settings.REDIS_URL)
    except Exception as exc:  # noqa: BLE001 — Redis может быть недоступен вне docker compose
        logger.warning("ordo_api.job_queue_unavailable", error=str(exc))
    yield
    logger.info("ordo_api.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(title="Ordo API", version="0.1.0", lifespan=lifespan)

    # Заменяется реальной очередью на Redis в lifespan; в тестах остаётся
    # заглушкой, так как ASGI-транспорт в тестах не запускает lifespan.
    app.state.job_queue = InMemoryJobQueue()

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(boards.router)
    app.include_router(tasks.router)
    app.include_router(today.router)
    app.include_router(files.router)
    app.include_router(suggestions.router)
    app.include_router(calendars.router)
    app.include_router(search.router)

    return app


app = create_app()
