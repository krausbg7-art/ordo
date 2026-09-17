import structlog
from arq import cron
from arq.connections import RedisSettings
from ordo_api.config import get_settings

from .tasks import process_file, sync_all_caldav_accounts, sync_calendar_account

settings = get_settings()
logger = structlog.get_logger(__name__)


async def startup(ctx):
    logger.info("ordo_worker.startup")


async def shutdown(ctx):
    logger.info("ordo_worker.shutdown")


async def ping(ctx) -> str:
    return "pong"


class WorkerSettings:
    functions = [ping, process_file, sync_calendar_account]
    cron_jobs = [cron(sync_all_caldav_accounts, minute={0, 15, 30, 45})]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
