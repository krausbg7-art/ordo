import structlog
from arq.connections import RedisSettings
from ordo_api.config import get_settings

from .tasks import process_file

settings = get_settings()
logger = structlog.get_logger(__name__)


async def startup(ctx):
    logger.info("ordo_worker.startup")


async def shutdown(ctx):
    logger.info("ordo_worker.shutdown")


async def ping(ctx) -> str:
    return "pong"


class WorkerSettings:
    functions = [ping, process_file]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
