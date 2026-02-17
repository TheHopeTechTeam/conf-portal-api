"""
NotificationHandler: user-facing notification APIs (list all with read status, mark read).
"""
from uuid import UUID

from portal.exceptions.responses import ForbiddenException, NotFoundException
from portal.libs.contexts.user_context import get_user_context
from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import (
    PortalNotification,
    PortalNotificationHistory,
    PortalFcmDevice,
    PortalFcmUserDevice,
)
from portal.serializers.v1.notification import (
    UserNotificationItem,
    UserNotificationList,
)


class NotificationHandler:
    """NotificationHandler: get all notifications (with read status) and mark as read for current user."""

    def __init__(self, session: Session):
        self._session = session

    def _require_user_id(self) -> UUID:
        user_ctx = get_user_context()
        if not user_ctx or not user_ctx.user_id:
            raise ForbiddenException(detail="Authentication required")
        return user_ctx.user_id

    @distributed_trace()
    async def get_notifications(self) -> UserNotificationList:
        """
        Get all notifications for the current user (across all user's devices), each with is_read.
        :return: List of notification history items with notification content and read status.
        """
        user_id = self._require_user_id()
        items = await (
            self._session.select(
                PortalNotificationHistory.id,
                PortalNotificationHistory.is_read,
                PortalNotificationHistory.created_at,
                PortalNotification.title,
                PortalNotification.message,
                PortalNotification.url,
            )
            .select_from(PortalNotificationHistory)
            .join(
                PortalFcmDevice,
                PortalNotificationHistory.device_id == PortalFcmDevice.id,
            )
            .join(
                PortalFcmUserDevice,
                PortalFcmDevice.id == PortalFcmUserDevice.device_id,
            )
            .join(
                PortalNotification,
                PortalNotificationHistory.notification_id == PortalNotification.id,
            )
            .where(PortalFcmUserDevice.user_id == user_id)
            .where(PortalNotificationHistory.is_deleted == False)
            .order_by(PortalNotificationHistory.created_at.desc())
            .fetch(as_model=UserNotificationItem)
        )
        return UserNotificationList(items=items)

    @distributed_trace()
    async def mark_notification_as_read(self, notification_history_id: UUID) -> None:
        """
        Mark a single notification history as read. The record must belong to current user's device.
        :param notification_history_id: PortalNotificationHistory id
        :return:
        """
        user_id = self._require_user_id()
        device_ids = await (
            self._session.select(PortalFcmUserDevice.device_id)
            .where(PortalFcmUserDevice.user_id == user_id)
            .fetch()
        )
        device_id_set = {row["device_id"] for row in device_ids}
        if not device_id_set:
            raise NotFoundException(detail="Notification not found")

        history = await (
            self._session.select(
                PortalNotificationHistory.id,
                PortalNotificationHistory.device_id,
            )
            .where(PortalNotificationHistory.id == notification_history_id)
            .where(PortalNotificationHistory.is_deleted == False)
            .fetchrow()
        )
        if not history or history["device_id"] not in device_id_set:
            raise NotFoundException(detail="Notification not found")

        await (
            self._session.update(PortalNotificationHistory)
            .values(is_read=True)
            .where(PortalNotificationHistory.id == notification_history_id)
            .execute()
        )

    @distributed_trace()
    async def mark_all_notifications_as_read(self) -> None:
        """
        Mark all notification history for the current user's devices as read.
        :return:
        """
        user_id = self._require_user_id()
        device_ids = await (
            self._session.select(PortalFcmUserDevice.device_id)
            .where(PortalFcmUserDevice.user_id == user_id)
            .fetch()
        )
        device_id_list = [row["device_id"] for row in device_ids]
        if not device_id_list:
            return

        await (
            self._session.update(PortalNotificationHistory)
            .values(is_read=True)
            .where(PortalNotificationHistory.device_id.in_(device_id_list))
            .where(PortalNotificationHistory.is_read == False)
            .where(PortalNotificationHistory.is_deleted == False)
            .execute()
        )
