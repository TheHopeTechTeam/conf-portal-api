"""
Admin event info API routes
"""
import uuid

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, status

from portal.container import Container
from portal.handlers import AdminEventInfoHandler
from portal.libs.consts.permission import Permission
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.admin.event_info import (
    AdminEventInfoDetail,
    AdminEventInfoList,
    AdminEventInfoCreate,
    AdminEventInfoUpdate,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/{conference_id}/list",
    status_code=status.HTTP_200_OK,
    response_model=AdminEventInfoList,
    permissions=[
        Permission.CONFERENCE_EVENT_SCHEDULE.read
    ]
)
@inject
async def get_event_info_list(
    conference_id: uuid.UUID,
    admin_event_info_handler: AdminEventInfoHandler = Depends(Provide[Container.admin_event_info_handler]),
):
    """

    :param conference_id:
    :param admin_event_info_handler:
    :return:
    """
    return await admin_event_info_handler.get_event_info_list(conference_id=conference_id)


@router.get(
    path="/{event_info_id}",
    status_code=status.HTTP_200_OK,
    response_model=AdminEventInfoDetail,
    permissions=[
        Permission.CONFERENCE_EVENT_SCHEDULE.read
    ]
)
@inject
async def get_event_info_detail(
    event_info_id: uuid.UUID,
    admin_event_info_handler: AdminEventInfoHandler = Depends(Provide[Container.admin_event_info_handler]),
):
    """

    :param event_info_id:
    :param admin_event_info_handler:
    :return:
    """
    return await admin_event_info_handler.get_event_info_by_id(event_id=event_info_id)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel,
    permissions=[
        Permission.CONFERENCE_EVENT_SCHEDULE.create
    ]
)
@inject
async def create_event_info(
    event_info_data: AdminEventInfoCreate,
    admin_event_info_handler: AdminEventInfoHandler = Depends(Provide[Container.admin_event_info_handler]),
):
    """

    :param event_info_data:
    :param admin_event_info_handler:
    :return:
    """
    return await admin_event_info_handler.create_event_info(model=event_info_data)


@router.put(
    path="/{event_info_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    permissions=[
        Permission.CONFERENCE_EVENT_SCHEDULE.modify
    ]
)
@inject
async def update_event_info(
    event_info_id: uuid.UUID,
    event_info_data: AdminEventInfoUpdate,
    admin_event_info_handler: AdminEventInfoHandler = Depends(Provide[Container.admin_event_info_handler]),
):
    """

    :param event_info_id:
    :param event_info_data:
    :param admin_event_info_handler:
    :return:
    """
    return await admin_event_info_handler.update_event_info(event_id=event_info_id, model=event_info_data)


@router.delete(
    path="/{event_info_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    permissions=[
        Permission.CONFERENCE_EVENT_SCHEDULE.delete
    ]
)
@inject
async def delete_event_info(
    event_info_id: uuid.UUID,
    admin_event_info_handler: AdminEventInfoHandler = Depends(Provide[Container.admin_event_info_handler]),
):
    """

    :param event_info_id:
    :param admin_event_info_handler:
    :return:
    """
    return await admin_event_info_handler.delete_event_info(event_id=event_info_id)
