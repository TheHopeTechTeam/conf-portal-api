"""
User notification API (list all with read status, mark single read, mark all read)
"""
import uuid

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, status

from portal.container import Container
from portal.handlers import NotificationHandler
from portal.routers.auth_router import AuthRouter
from portal.serializers.v1.notification import UserNotificationList

router: AuthRouter = AuthRouter(is_admin=False)


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=UserNotificationList,
    description="Get all notifications for the current user, each with read status",
    operation_id="get_notifications",
)
@inject
async def get_notifications(
    notification_handler: NotificationHandler = Depends(Provide[Container.notification_handler]),
) -> UserNotificationList:
    """
    Get all notifications for the current user. Each item includes is_read.
    """
    return await notification_handler.get_notifications()


@router.patch(
    path="/history/{notification_history_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Mark a single notification as read",
    operation_id="mark_notification_as_read",
)
@inject
async def mark_notification_as_read(
    notification_history_id: uuid.UUID,
    notification_handler: NotificationHandler = Depends(Provide[Container.notification_handler]),
) -> None:
    """
    Mark a single notification (by notification history id) as read.
    The notification must belong to the current user's device.
    """
    await notification_handler.mark_notification_as_read(
        notification_history_id=notification_history_id
    )


@router.post(
    path="/read_all",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Mark all notifications as read for the current user",
    operation_id="mark_all_notifications_as_read",
)
@inject
async def mark_all_notifications_as_read(
    notification_handler: NotificationHandler = Depends(Provide[Container.notification_handler]),
) -> None:
    """
    Mark all notifications as read for the current user (all devices).
    """
    await notification_handler.mark_all_notifications_as_read()
