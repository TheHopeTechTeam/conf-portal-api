"""
ARQ Redis pool for enqueueing background jobs from the API process.
"""

import asyncio
from dataclasses import replace
from typing import Optional
from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from portal.config import settings
from portal.exceptions.responses.base import ApiBaseException
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger

# ARQ Redis sorted-set queue key for notification jobs (code constant, not env).
ARQ_NOTIFICATION_QUEUE_NAME = "conf-portal-api:notification"

_arq_pool: Optional[ArqRedis] = None
_arq_pool_lock = asyncio.Lock()


def get_arq_redis_settings() -> RedisSettings:
    """
    Redis settings for ARQ (broker). Uses ARQ_REDIS_URL with ARQ_REDIS_DB.
    """
    base_url = settings.ARQ_REDIS_URL
    if not base_url:
        raise ValueError("Redis is not configured; set ARQ_REDIS_URL")
    parsed = RedisSettings.from_dsn(base_url)
    return replace(parsed, database=settings.ARQ_REDIS_DB)


async def get_arq_pool() -> ArqRedis:
    """
    Lazy singleton pool for the current process.
    """
    global _arq_pool
    if _arq_pool is not None:
        return _arq_pool
    async with _arq_pool_lock:
        if _arq_pool is None:
            redis_settings = get_arq_redis_settings()
            _arq_pool = await create_pool(
                redis_settings,
                default_queue_name=ARQ_NOTIFICATION_QUEUE_NAME,
            )
        return _arq_pool


async def close_arq_pool() -> None:
    """
    Close the ARQ pool (e.g. on app shutdown).
    """
    global _arq_pool
    if _arq_pool is None:
        return
    try:
        await _arq_pool.close(close_connection_pool=True)
    except Exception as exc:
        logger.warning("close_arq_pool failed: %s", exc, exc_info=True)
    finally:
        _arq_pool = None


@distributed_trace()
async def enqueue_send_notification(notification_id: UUID, payload: dict) -> None:
    """
    Enqueue notification send job for the ARQ worker.
    """
    try:
        pool = await get_arq_pool()
    except ValueError as exc:
        raise ApiBaseException(status_code=503, detail=str(exc)) from exc
    await pool.enqueue_job(
        "send_notification_task",
        str(notification_id),
        payload,
        _queue_name=ARQ_NOTIFICATION_QUEUE_NAME,
    )
