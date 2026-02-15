"""
Admin notification API routes
"""
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminNotificationHandler
from portal.libs.consts.permission import Permission
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.admin.notification import (
    AdminNotificationCreate,
    AdminNotificationQuery,
    AdminNotificationPages,
    AdminNotificationHistoryQuery,
    AdminNotificationHistoryPages,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=AdminNotificationPages,
    permissions=[
        Permission.COMMS_NOTIFICATION.read
    ]
)
@inject
async def get_notification_pages(
    query_model: Annotated[AdminNotificationQuery, Query()],
    admin_notification_handler: AdminNotificationHandler = Depends(Provide[Container.admin_notification_handler])
):
    """
    Get notification pages
    :param query_model:
    :param admin_notification_handler:
    :return:
    """
    return await admin_notification_handler.get_notification_pages(model=query_model)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel,
    permissions=[
        Permission.COMMS_NOTIFICATION.create
    ]
)
@inject
async def create_notification(
    notification_data: AdminNotificationCreate,
    admin_notification_handler: AdminNotificationHandler = Depends(Provide[Container.admin_notification_handler])
):
    """
    Create and send notification
    :param notification_data:
    :param admin_notification_handler:
    :return:
    """
    return await admin_notification_handler.create_notification(model=notification_data)


@router.get(
    path="/history/pages",
    status_code=status.HTTP_200_OK,
    response_model=AdminNotificationHistoryPages,
    permissions=[
        Permission.COMMS_NOTIFICATION_HISTORY.read
    ]
)
@inject
async def get_notification_history_pages(
    query_model: Annotated[AdminNotificationHistoryQuery, Query()],
    admin_notification_handler: AdminNotificationHandler = Depends(Provide[Container.admin_notification_handler])
):
    """
    Get notification history pages with user info
    :param query_model:
    :param admin_notification_handler:
    :return:
    """
    return await admin_notification_handler.get_notification_history_pages(model=query_model)
