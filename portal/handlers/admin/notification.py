"""
AdminNotificationHandler
"""
import uuid

import sqlalchemy as sa

from portal.exceptions.responses.base import ApiBaseException
from portal.libs.consts.enums import NotificationMethod, NotificationType, NotificationStatus
from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.events.types import NotificationCreatedEvent
from portal.libs.events.publisher import publish_event_in_background
from portal.libs.logger import logger
from portal.models import (
    PortalNotification,
    PortalNotificationHistory,
    PortalFcmDevice,
    PortalFcmUserDevice,
    PortalUser,
    PortalUserProfile,
)
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.admin.notification import (
    AdminNotificationCreate,
    AdminNotificationItem,
    AdminNotificationHistoryItem,
    AdminNotificationHistoryQuery,
    AdminNotificationHistoryPages,
    AdminNotificationQuery,
    AdminNotificationPages,
)


class AdminNotificationHandler:
    """AdminNotificationHandler"""

    def __init__(
        self,
        session: Session,
    ):
        self._session = session

    @distributed_trace()
    async def create_notification(self, model: AdminNotificationCreate) -> UUIDBaseModel:
        """
        Create and send notification
        :param model:
        :return:
        """
        if model.type == NotificationType.INDIVIDUAL:
            if not model.user_ids or len(model.user_ids) != 1:
                raise ApiBaseException(
                    status_code=400,
                    detail="INDIVIDUAL type requires exactly one user_id",
                )
        elif model.type == NotificationType.MULTIPLE:
            if not model.user_ids or len(model.user_ids) < 1:
                raise ApiBaseException(
                    status_code=400,
                    detail="MULTIPLE type requires at least one user_id",
                )
        # SYSTEM type: user_ids ignored, no validation

        notification_id = uuid.uuid4()

        # Create notification record
        await (
            self._session.insert(PortalNotification)
            .values(
                id=notification_id,
                title=model.title,
                message=model.message,
                url=model.url,
                method=model.method.value,
                type=model.type.value,
                status=NotificationStatus.PENDING.value,
                failure_count=0,
                success_count=0,
            )
            .execute()
        )

        # Publish event for async notification sending
        publish_event_in_background(event=NotificationCreatedEvent(notification_id=notification_id, model=model))

        logger.info(f"Notification {notification_id} created and event published for sending")

        return UUIDBaseModel(id=notification_id)

    @distributed_trace()
    async def get_notification_pages(self, model: AdminNotificationQuery) -> AdminNotificationPages:
        """
        Get notification pages
        :param model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalNotification.id,
                PortalNotification.title,
                PortalNotification.message,
                PortalNotification.url,
                PortalNotification.method,
                PortalNotification.type,
                PortalNotification.status,
                PortalNotification.failure_count,
                PortalNotification.success_count,
                PortalNotification.created_at,
                PortalNotification.updated_at,
            )
            .where(PortalNotification.is_deleted == model.deleted)
            .where(
                model.keyword, lambda: sa.or_(
                    PortalNotification.title.ilike(f"%{model.keyword}%"),
                    PortalNotification.message.ilike(f"%{model.keyword}%"),
                )
            )
            .where(model.method is not None, lambda: PortalNotification.method == model.method.value)
            .where(model.type is not None, lambda: PortalNotification.type == model.type.value)
            .where(model.status is not None, lambda: PortalNotification.status == model.status.value)
            .order_by_with(
                tables=[PortalNotification],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=AdminNotificationItem
            )
        )
        return AdminNotificationPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def get_notification_history_pages(self, model: AdminNotificationHistoryQuery) -> AdminNotificationHistoryPages:
        """
        Get notification history pages with user info
        :param model:
        :return:
        """
        query = (
            self._session.select(
                PortalNotificationHistory.id,
                PortalNotificationHistory.notification_id,
                PortalNotificationHistory.device_id,
                PortalNotificationHistory.message_id,
                PortalNotificationHistory.exception,
                PortalNotificationHistory.status,
                PortalNotificationHistory.is_read,
                PortalNotificationHistory.created_at,
                PortalNotificationHistory.updated_at,
                PortalUser.id.label("user_id"),
                PortalUser.email.label("user_email"),
                PortalUser.phone_number.label("user_phone_number"),
                PortalUserProfile.display_name.label("user_display_name"),
            )
            .outerjoin(
                PortalFcmDevice,
                PortalNotificationHistory.device_id == PortalFcmDevice.id
            )
            .outerjoin(
                PortalFcmUserDevice,
                PortalFcmDevice.id == PortalFcmUserDevice.device_id
            )
            .outerjoin(
                PortalUser,
                PortalFcmUserDevice.user_id == PortalUser.id
            )
            .outerjoin(
                PortalUserProfile,
                PortalUser.id == PortalUserProfile.user_id
            )
            .where(PortalNotificationHistory.is_deleted == model.deleted)
            .where(
                model.keyword, lambda: sa.or_(
                    PortalNotificationHistory.message_id.ilike(f"%{model.keyword}%"),
                    PortalUser.email.ilike(f"%{model.keyword}%"),
                    PortalUserProfile.display_name.ilike(f"%{model.keyword}%"),
                )
            )
            .where(
                model.notification_id is not None,
                lambda: PortalNotificationHistory.notification_id == model.notification_id
            )
            .where(
                model.user_id is not None,
                lambda: PortalUser.id == model.user_id
            )
            .where(
                model.status is not None,
                lambda: PortalNotificationHistory.status == model.status.value
            )
            .order_by_with(
                tables=[PortalNotificationHistory],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
        )

        items, count = await query.fetchpages(
            no_order_by=False,
            as_model=AdminNotificationHistoryItem
        )

        return AdminNotificationHistoryPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )
