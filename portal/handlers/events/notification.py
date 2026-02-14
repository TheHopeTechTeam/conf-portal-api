"""
Notification event handlers
"""
from uuid import UUID

from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError

from portal.config import settings
from portal.exceptions.responses.base import ApiBaseException
from portal.libs.consts.enums import (
    NotificationMethod,
    NotificationType,
    NotificationStatus,
    NotificationHistoryStatus,
)
from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.events.base import EventHandler
from portal.libs.events.types import NotificationCreatedEvent
from portal.libs.logger import logger
from portal.models import (
    PortalNotification,
    PortalNotificationHistory,
    PortalFcmDevice,
    PortalFcmUserDevice,
)
from portal.serializers.v1.admin.notification import AdminNotificationCreate


class NotificationCreatedEventHandler(EventHandler):
    """
    Handler for NotificationCreatedEvent
    """

    def __init__(self, session: Session):
        """
        Initialize handler
        :param session:
        """
        self._session = session

    @property
    def event_type(self) -> type[NotificationCreatedEvent]:
        """
        Return the event type this handler handles
        :return:
        """
        return NotificationCreatedEvent

    @distributed_trace()
    async def handle(self, event: NotificationCreatedEvent) -> None:
        """
        Handle notification created event - send the notification
        :param event:
        :return:
        """
        logger.info(
            "Processing notification created event: %s, method=%s, type=%s",
            event.notification_id,
            event.model.method,
            event.model.type
        )

        try:
            # Build AdminNotificationCreate model from event

            if event.model.dry_run or not settings.ENABLE_PUSH_NOTIFICATION:
                await self._handle_dry_run(event.notification_id, event.model)
                return

            # Send notification based on method
            if event.model.method == NotificationMethod.PUSH:
                await self._send_push_notification(
                    event.notification_id, event.model
                )
            elif event.model.method == NotificationMethod.EMAIL:
                await self._send_email_notification(
                    event.notification_id, event.model
                )
            else:
                logger.error("Invalid notification method: %s", event.model.method)
                raise ValueError(f"Invalid notification method: {event.model.method}")

            logger.info(
                "Successfully sent notification %s",
                event.notification_id
            )
        except Exception as e:
            logger.error(
                "Failed to send notification %s: %s",
                event.notification_id,
                str(e),
                exc_info=True
            )
            # Update notification status to failed
            try:
                await (
                    self._session.update(PortalNotification)
                    .values(status=NotificationStatus.FAILED.value)
                    .where(PortalNotification.id == event.notification_id)
                    .execute()
                )
            except Exception as update_error:
                logger.error(
                    "Failed to update notification status: %s",
                    str(update_error),
                    exc_info=True
                )
            # Re-raise to allow event bus to handle
            raise

    @distributed_trace()
    async def _handle_dry_run(self, notification_id: UUID, model: AdminNotificationCreate) -> None:
        """
        Resolve targets and mark notification as dry run without sending.
        """
        if model.method == NotificationMethod.PUSH:
            tokens, device_ids = await self._resolve_push_targets(model)
            target_count = len(device_ids)
            logger.info(
                "Dry run notification %s: would send push to %s device(s)",
                notification_id,
                target_count,
            )
        else:
            target_count = 0
            logger.info(
                "Dry run notification %s: email method not implemented for dry run",
                notification_id,
            )

        await (
            self._session.update(PortalNotification)
            .values(
                status=NotificationStatus.DRY_RUN.value,
                success_count=target_count,
                failure_count=0,
            )
            .where(PortalNotification.id == notification_id)
            .execute()
        )

    @distributed_trace()
    async def _resolve_push_targets(
        self, model: AdminNotificationCreate
    ) -> tuple[list[str], list[UUID]]:
        """
        Resolve push notification targets (tokens and device_ids). Used by both
        dry run and actual send.
        - SYSTEM: all FCM devices in DB (no user filter).
        - INDIVIDUAL/MULTIPLE: devices linked to the given user_ids.
        """
        if model.type == NotificationType.SYSTEM:
            device_tokens = await (
                self._session.select(
                    PortalFcmDevice.id,
                    PortalFcmDevice.token,
                )
                .select_from(PortalFcmDevice)
                .fetch()
            )
            tokens = [row.token for row in device_tokens if row.token]
            device_ids = [row.id for row in device_tokens]
            return tokens, device_ids

        if not model.user_ids:
            logger.warning("No user IDs specified for push notification")
            return [], []

        device_tokens = await (
            self._session.select(
                PortalFcmDevice.id,
                PortalFcmDevice.token,
            )
            .join(PortalFcmUserDevice, PortalFcmDevice.id == PortalFcmUserDevice.device_id)
            .where(PortalFcmUserDevice.user_id.in_(model.user_ids))
            .fetch()
        )
        tokens = [row.token for row in device_tokens if row.token]
        device_ids = [row.id for row in device_tokens]

        return tokens, device_ids

    @distributed_trace()
    async def _send_push_notification(self, notification_id: UUID, model: AdminNotificationCreate) -> None:
        """
        Send push notification
        :param notification_id:
        :param model:
        :return:
        """
        tokens, device_ids = await self._resolve_push_targets(model)

        if not tokens:
            raise ApiBaseException(status_code=400, detail="No valid device tokens found")

        # Send push notification
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

        multicast_message = messaging.MulticastMessage(
            notification=notification,
            data=data,
            tokens=tokens,
        )

        try:
            result = messaging.send_each_for_multicast(multicast_message)
            success_count = result.success_count
            failure_count = result.failure_count

            # Create history records
            history_records = []
            for i, device_id in enumerate(device_ids):
                if i < len(result.responses):
                    response = result.responses[i]
                    if response.success:
                        status = NotificationHistoryStatus.SUCCESS.value
                        message_id = response.message_id
                        exception = None
                    else:
                        status = NotificationHistoryStatus.FAILED.value
                        message_id = None
                        exception = str(response.exception) if response.exception else "Unknown error"
                else:
                    status = NotificationHistoryStatus.FAILED.value
                    message_id = None
                    exception = "No response"

                history_records.append({
                    "notification_id": notification_id,
                    "device_id": device_id,
                    "message_id": message_id,
                    "exception": exception,
                    "status": status,
                })

            if history_records:
                await (
                    self._session.insert(PortalNotificationHistory)
                    .values(history_records)
                    .execute()
                )

            # Update notification counts and status
            final_status = NotificationStatus.SENT.value if success_count > 0 else NotificationStatus.FAILED.value
            await (
                self._session.update(PortalNotification)
                .values(
                    success_count=success_count,
                    failure_count=failure_count,
                    status=final_status,
                )
                .where(PortalNotification.id == notification_id)
                .execute()
            )

        except FirebaseError as e:
            logger.error("Firebase error: %s", str(e))
            # Create failed history records
            history_records = []
            for device_id in device_ids:
                history_records.append({
                    "notification_id": notification_id,
                    "device_id": device_id,
                    "status": NotificationHistoryStatus.FAILED.value,
                    "exception": str(e),
                })

            if history_records:
                await (
                    self._session.insert(PortalNotificationHistory)
                    .values(history_records)
                    .execute()
                )

            await (
                self._session.update(PortalNotification)
                .values(
                    failure_count=len(device_ids),
                    status=NotificationStatus.FAILED.value,
                )
                .where(PortalNotification.id == notification_id)
                .execute()
            )
            raise ApiBaseException(
                status_code=500,
                detail=f"Failed to send push notification: {str(e)}"
            )

    @distributed_trace()
    async def _send_email_notification(self, notification_id: UUID, model: AdminNotificationCreate) -> None:
        """
        Send email notification
        :param notification_id:
        :param model:
        :return:
        """
        raise NotImplementedError("Email notification sending is not implemented yet")
