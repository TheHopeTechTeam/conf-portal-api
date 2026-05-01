"""
ARQ worker: processes notification send jobs.
"""

from urllib.parse import urlparse
from uuid import UUID

import sentry_sdk
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from portal.config import settings
from portal.container import Container
from portal.handlers.events.notification import NotificationCreatedEventHandler
from portal.libs.contexts.event_session_context import reset_event_session, set_event_session
from portal.libs.events.publisher import set_global_container
from portal.libs.events.types import NotificationCreatedEvent
from portal.libs.firebase_init import init_firebase_safe
from portal.libs.logger import logger
from portal.queues.arq_pool import ARQ_NOTIFICATION_QUEUE_NAME, close_arq_pool, get_arq_redis_settings
from portal.serializers.v1.admin.notification import AdminNotificationCreate


def _setup_worker_sentry() -> None:
    """
    Initialize Sentry for the worker process (no FastAPI integration).
    """
    if not settings.SENTRY_URL:
        return

    def before_send_transaction(event, hint):
        request = (event or {}).get("request") or {}
        url = request.get("url")
        if not url:
            return event
        path = urlparse(url).path or ""
        if not path:
            return event
        if path.startswith("/admin"):
            event["tags"] = {"is_admin": "true"}
        else:
            event["tags"] = {"is_admin": "false"}
        event["transaction"] = path.strip()
        return event

    sentry_sdk.init(
        dsn=settings.SENTRY_URL,
        release=settings.APP_VERSION,
        integrations=[
            AsyncPGIntegration(),
            HttpxIntegration(),
            RedisIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=settings.ENV.upper(),
        before_send_transaction=before_send_transaction,
        enable_logs=True,
    )


async def worker_startup(ctx: dict) -> None:
    """
    Build DI container and shared clients for job execution.
    """
    container = Container()
    ctx["container"] = container
    set_global_container(container)
    init_firebase_safe()
    _setup_worker_sentry()
    logger.info("ARQ worker startup complete")


async def worker_shutdown(ctx: dict) -> None:
    """
    Release resources on worker exit.
    """
    await close_arq_pool()
    set_global_container(None)
    ctx.pop("container", None)
    logger.info("ARQ worker shutdown complete")


async def send_notification_task(ctx: dict, notification_id_str: str, payload: dict) -> None:
    """
    Run NotificationCreatedEventHandler for one notification (same logic as in-process event bus).
    """
    container: Container = ctx.get("container")
    if container is None:
        raise RuntimeError("ARQ worker container missing; on_startup did not run")

    model = AdminNotificationCreate(**payload)
    notification_id = UUID(notification_id_str)
    event = NotificationCreatedEvent(notification_id=notification_id, model=model)

    session = container.db_session()
    token = set_event_session(session)
    handler = NotificationCreatedEventHandler(session=session)
    try:
        logger.info("-" * 100)
        await handler.handle(event)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        reset_event_session(token)
        await session.close()
        logger.info("-" * 100)


class WorkerSettings:
    """
    ARQ worker configuration (arq CLI: arq portal.workers.arq_worker.WorkerSettings).
    """

    functions = [send_notification_task]
    redis_settings = get_arq_redis_settings()
    queue_name = ARQ_NOTIFICATION_QUEUE_NAME
    job_timeout = settings.ARQ_JOB_TIMEOUT
    max_tries = settings.ARQ_MAX_TRIES
    on_startup = worker_startup
    on_shutdown = worker_shutdown
