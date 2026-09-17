from typing import Protocol

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import Request


class JobQueue(Protocol):
    async def enqueue_job(self, function: str, *args) -> None: ...


class ArqJobQueue:
    def __init__(self, redis: ArqRedis):
        self._redis = redis

    async def enqueue_job(self, function: str, *args) -> None:
        await self._redis.enqueue_job(function, *args)


class InMemoryJobQueue:
    """Очередь-заглушка для тестов — не требует Redis."""

    def __init__(self):
        self.jobs: list[tuple[str, tuple]] = []

    async def enqueue_job(self, function: str, *args) -> None:
        self.jobs.append((function, args))


async def create_arq_job_queue(redis_url: str) -> ArqJobQueue:
    redis = await create_pool(RedisSettings.from_dsn(redis_url))
    return ArqJobQueue(redis)


def get_job_queue(request: Request) -> JobQueue:
    return request.app.state.job_queue
