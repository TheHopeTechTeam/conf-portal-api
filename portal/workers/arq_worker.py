"""
ARQ worker: processes notification send jobs.
"""

from urllib.parse import urlparse
from uuid import UUID

import sentry_sdk
import sqlalchemy as sa
from arq.connections import ArqRedis
from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from portal.config import settings
from portal.container import Container
from portal.handlers.events.notification import NotificationCreatedEventHandler
from portal.libs.consts.enums import (
    NotificationHistoryStatus,
    NotificationMethod,
    NotificationStatus,
)
from portal.libs.contexts.event_session_context import reset_event_session, set_event_session
from portal.libs.events.publisher import set_global_container
from portal.libs.events.types import NotificationCreatedEvent
from portal.libs.firebase_init import init_firebase_safe
from portal.libs.logger import logger
from portal.models import PortalNotification, PortalNotificationHistory
from portal.models.mixins.context import SYSTEM_USER_ID
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


async def _run_handler_in_session(container: Container, event: NotificationCreatedEvent) -> None:
    """
    Execute existing notification handler with event-scoped session lifecycle.
    """
    session = container.db_session()
    token = set_event_session(session)
    handler = NotificationCreatedEventHandler(session=session)
    try:
        await handler.handle(event)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        reset_event_session(token)
        await session.close()


async def send_notification_chunk_task(
    ctx: dict,
    notification_id_str: str,
    payload: dict,
    batch_tokens: list[str],
    batch_device_id_strs: list[str],
    chunk_index: int,
    total_chunks: int,
) -> None:
    """
    Send one FCM chunk: pre-write PENDING history (commit), send FCM, back-fill history, update counts.
    """
    container: Container = ctx.get("container")
    if container is None:
        raise RuntimeError("ARQ worker container missing; on_startup did not run")

    model = AdminNotificationCreate(**payload)
    notification_id = UUID(notification_id_str)
    batch_device_ids = [UUID(device_id) for device_id in batch_device_id_strs]
    logger.info(
        "Chunk task started notification_id=%s chunk=%s/%s method=%s token_count=%s",
        notification_id,
        chunk_index,
        total_chunks,
        model.method,
        len(batch_tokens),
    )

    notification = messaging.Notification(
        title=model.title,
        body=model.message,
    )
    data = {
        "notification_id": str(notification_id),
        "type": str(model.type.value),
    }
    if model.url:
        data["url"] = model.url

    session = container.db_session()
    token = set_event_session(session)
    try:
        pending_records = [
            {
                "notification_id": notification_id,
                "device_id": device_id,
                "message_id": None,
                "exception": None,
                "status": NotificationHistoryStatus.PENDING.value,
                "created_by": "system",
                "created_by_id": SYSTEM_USER_ID,
                "updated_by": "system",
                "updated_by_id": SYSTEM_USER_ID,
                "is_read": False,
                "is_deleted": False,
            }
            for device_id in batch_device_ids
        ]
        if pending_records:
            await (
                session.insert(PortalNotificationHistory)
                .values(pending_records)
                .on_conflict_do_nothing(index_elements=["notification_id", "device_id"])
                .execute()
            )
        await session.commit()
        logger.info(
            "Chunk pre-write PENDING committed notification_id=%s chunk=%s/%s row_count=%s",
            notification_id,
            chunk_index,
            total_chunks,
            len(pending_records),
        )

        multicast_message = messaging.MulticastMessage(
            notification=notification,
            data=data,
            tokens=batch_tokens,
        )
        try:
            result = messaging.send_each_for_multicast(multicast_message)
        except FirebaseError as exc:
            logger.warning(
                "FCM FirebaseError in chunk notification_id=%s chunk=%s/%s token_count=%s error=%s",
                notification_id,
                chunk_index,
                total_chunks,
                len(batch_tokens),
                exc,
            )
            await (
                session.update(PortalNotificationHistory)
                .values(
                    status=NotificationHistoryStatus.FAILED.value,
                    message_id=None,
                    exception=str(exc),
                    updated_by="system",
                    updated_by_id=SYSTEM_USER_ID,
                )
                .where(PortalNotificationHistory.notification_id == notification_id)
                .where(PortalNotificationHistory.device_id.in_(batch_device_ids))
                .execute()
            )
            await (
                session.update(PortalNotification)
                .values(
                    failure_count=PortalNotification.failure_count + len(batch_device_ids),
                )
                .where(PortalNotification.id == notification_id)
                .execute()
            )
            await (
                session.update(PortalNotification)
                .values(status=NotificationStatus.FAILED.value)
                .where(PortalNotification.id == notification_id)
                .where(PortalNotification.success_count == 0)
                .execute()
            )
            await session.commit()
            raise

        success_count = result.success_count
        failure_count = result.failure_count
        logger.info(
            "FCM chunk sent notification_id=%s chunk=%s/%s token_count=%s success=%s failure=%s",
            notification_id,
            chunk_index,
            total_chunks,
            len(batch_tokens),
            success_count,
            failure_count,
        )

        for index, device_id in enumerate(batch_device_ids):
            if index < len(result.responses):
                response = result.responses[index]
                if response.success:
                    await (
                        session.update(PortalNotificationHistory)
                        .values(
                            status=NotificationHistoryStatus.SUCCESS.value,
                            message_id=response.message_id,
                            exception=None,
                            updated_by="system",
                            updated_by_id=SYSTEM_USER_ID,
                        )
                        .where(PortalNotificationHistory.notification_id == notification_id)
                        .where(PortalNotificationHistory.device_id == device_id)
                        .execute()
                    )
                else:
                    exception_text = (
                        str(response.exception) if response.exception else "Unknown error"
                    )
                    await (
                        session.update(PortalNotificationHistory)
                        .values(
                            status=NotificationHistoryStatus.FAILED.value,
                            message_id=None,
                            exception=exception_text,
                            updated_by="system",
                            updated_by_id=SYSTEM_USER_ID,
                        )
                        .where(PortalNotificationHistory.notification_id == notification_id)
                        .where(PortalNotificationHistory.device_id == device_id)
                        .execute()
                    )
            else:
                await (
                    session.update(PortalNotificationHistory)
                    .values(
                        status=NotificationHistoryStatus.FAILED.value,
                        message_id=None,
                        exception="No response",
                        updated_by="system",
                        updated_by_id=SYSTEM_USER_ID,
                    )
                    .where(PortalNotificationHistory.notification_id == notification_id)
                    .where(PortalNotificationHistory.device_id == device_id)
                    .execute()
                )

        await (
            session.update(PortalNotification)
            .values(
                success_count=PortalNotification.success_count + success_count,
                failure_count=PortalNotification.failure_count + failure_count,
            )
            .where(PortalNotification.id == notification_id)
            .execute()
        )
        if success_count > 0:
            await (
                session.update(PortalNotification)
                .values(status=NotificationStatus.SENT.value)
                .where(PortalNotification.id == notification_id)
                .execute()
            )
        else:
            await (
                session.update(PortalNotification)
                .values(status=NotificationStatus.FAILED.value)
                .where(PortalNotification.id == notification_id)
                .where(PortalNotification.success_count == 0)
                .execute()
            )
        await session.commit()
        logger.info(
            "Chunk task committed notification_id=%s chunk=%s/%s success_delta=%s failure_delta=%s",
            notification_id,
            chunk_index,
            total_chunks,
            success_count,
            failure_count,
        )
    except FirebaseError:
        # Already handled, committed, and re-raised from inner block; do not rollback.
        raise
    except Exception as exc:
        logger.exception(
            "Chunk task failed notification_id=%s chunk=%s/%s token_count=%s",
            notification_id,
            chunk_index,
            total_chunks,
            len(batch_tokens),
        )
        await session.rollback()
        try:
            pending_count_row = await (
                session.select(
                    sa.func.count(PortalNotificationHistory.id).label("pending_count")
                )
                .where(PortalNotificationHistory.notification_id == notification_id)
                .where(PortalNotificationHistory.device_id.in_(batch_device_ids))
                .where(PortalNotificationHistory.status == NotificationHistoryStatus.PENDING.value)
                .fetchrow()
            )
            pending_count = int((pending_count_row or {}).get("pending_count") or 0)
            if pending_count > 0:
                await (
                    session.update(PortalNotificationHistory)
                    .values(
                        status=NotificationHistoryStatus.FAILED.value,
                        message_id=None,
                        exception=str(exc),
                        updated_by="system",
                        updated_by_id=SYSTEM_USER_ID,
                    )
                    .where(PortalNotificationHistory.notification_id == notification_id)
                    .where(PortalNotificationHistory.device_id.in_(batch_device_ids))
                    .where(PortalNotificationHistory.status == NotificationHistoryStatus.PENDING.value)
                    .execute()
                )
                await (
                    session.update(PortalNotification)
                    .values(
                        failure_count=PortalNotification.failure_count + pending_count,
                    )
                    .where(PortalNotification.id == notification_id)
                    .execute()
                )
                await (
                    session.update(PortalNotification)
                    .values(status=NotificationStatus.FAILED.value)
                    .where(PortalNotification.id == notification_id)
                    .where(PortalNotification.success_count == 0)
                    .execute()
                )
                await session.commit()
                logger.warning(
                    "Chunk task fallback marked pending rows as FAILED notification_id=%s chunk=%s/%s pending_count=%s",
                    notification_id,
                    chunk_index,
                    total_chunks,
                    pending_count,
                )
        except Exception:
            await session.rollback()
            logger.exception(
                "Chunk task fallback failed notification_id=%s chunk=%s/%s token_count=%s",
                notification_id,
                chunk_index,
                total_chunks,
                len(batch_tokens),
            )
        raise
    finally:
        reset_event_session(token)
        await session.close()
        logger.info(
            "Chunk task finished notification_id=%s chunk=%s/%s token_count=%s",
            notification_id,
            chunk_index,
            total_chunks,
            len(batch_tokens),
        )


async def send_notification_task(ctx: dict, notification_id_str: str, payload: dict) -> None:
    """
    Parent notification task.
    - Non-push or dry-run: execute existing handler directly.
    - Push: fan out into multiple chunk tasks to keep each job short.
    """
    container: Container = ctx.get("container")
    if container is None:
        raise RuntimeError("ARQ worker container missing; on_startup did not run")

    model = AdminNotificationCreate(**payload)
    notification_id = UUID(notification_id_str)
    event = NotificationCreatedEvent(notification_id=notification_id, model=model)
    logger.info(
        "Parent task started notification_id=%s method=%s dry_run=%s",
        notification_id,
        model.method,
        model.dry_run,
    )

    if model.method != NotificationMethod.PUSH or model.dry_run:
        logger.info(
            "Parent task using direct handler path notification_id=%s method=%s dry_run=%s",
            notification_id,
            model.method,
            model.dry_run,
        )
        await _run_handler_in_session(container, event)
        logger.info("Parent task finished (direct path) notification_id=%s", notification_id)
        return

    # Resolve targets using existing handler implementation, then split into child chunk jobs.
    session = container.db_session()
    token = set_event_session(session)
    handler = NotificationCreatedEventHandler(session=session)
    try:
        tokens, device_ids = await handler._resolve_push_targets(model)
        logger.info(
            "Parent task resolved targets notification_id=%s token_count=%s",
            notification_id,
            len(tokens),
        )
        if not tokens:
            # Reuse existing handler behavior for no-token path (status update + failure semantics).
            logger.warning("Parent task found no tokens notification_id=%s", notification_id)
            await handler.handle(event)
            await session.commit()
            return
    except Exception:
        logger.exception("Parent task failed during target resolution notification_id=%s", notification_id)
        await session.rollback()
        raise
    finally:
        reset_event_session(token)
        await session.close()

    redis: ArqRedis | None = ctx.get("redis")
    if redis is None:
        raise RuntimeError("ARQ redis client missing in worker context")

    batch_size = settings.FCM_MAX_MULTICAST_TOKENS
    total_chunks = (len(tokens) + batch_size - 1) // batch_size
    chunk_count = 0
    for offset in range(0, len(tokens), batch_size):
        chunk_tokens = tokens[offset : offset + batch_size]
        chunk_device_ids = [
            str(device_id)
            for device_id in device_ids[offset : offset + batch_size]
        ]
        await redis.enqueue_job(
            "send_notification_chunk_task",
            str(notification_id),
            payload,
            chunk_tokens,
            chunk_device_ids,
            chunk_count + 1,
            total_chunks,
            _queue_name=ARQ_NOTIFICATION_QUEUE_NAME,
        )
        chunk_count += 1
        logger.info(
            "Enqueued chunk notification_id=%s chunk=%s/%s chunk_size=%s",
            notification_id,
            chunk_count,
            total_chunks,
            len(chunk_tokens),
        )
    logger.info(
        "Queued %s notification chunk jobs for %s targets (notification_id=%s)",
        chunk_count,
        len(tokens),
        notification_id,
    )
    logger.info("Parent task finished notification_id=%s", notification_id)


class WorkerSettings:
    """
    ARQ worker configuration (arq CLI: arq portal.workers.arq_worker.WorkerSettings).
    """

    functions = [send_notification_task, send_notification_chunk_task]
    redis_settings = get_arq_redis_settings()
    queue_name = ARQ_NOTIFICATION_QUEUE_NAME
    job_timeout = settings.ARQ_JOB_TIMEOUT
    max_tries = settings.ARQ_MAX_TRIES
    on_startup = worker_startup
    on_shutdown = worker_shutdown
