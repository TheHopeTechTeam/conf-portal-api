"""
Admin event info API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, Query, status

from portal.container import Container
from portal.handlers import AdminEventInfoHandler
from portal.libs.depends import check_admin_access_token
from portal.route_classes import LogRoute
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.admin.event_info import (
    EventInfoQuery,
    EventInfoDetail,
    EventInfoList,
    EventInfoCreate,
    EventInfoUpdate,
)

router = APIRouter(route_class=LogRoute, dependencies=[check_admin_access_token])


@router.get(
    path="/list",
    status_code=status.HTTP_200_OK,
    response_model=EventInfoList
)
@inject
async def get_event_info_list(
    query_model: Annotated[EventInfoQuery, Query()],
    admin_event_info_handler: AdminEventInfoHandler = Depends(Provide[Container.admin_event_info_handler]),
):
    """

    :param query_model:
    :param admin_event_info_handler:
    :return:
    """
    return await admin_event_info_handler.get_event_info_list(model=query_model)


@router.get(
    path="/{event_info_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventInfoDetail
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
    response_model=UUIDBaseModel
)
@inject
async def create_event_info(
    event_info_data: EventInfoCreate,
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
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_event_info(
    event_info_id: uuid.UUID,
    event_info_data: EventInfoUpdate,
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
    status_code=status.HTTP_204_NO_CONTENT
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
