"""
Event Info API Router
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Request, Response, Depends
from fastapi.params import Header
from starlette import status

from portal.container import Container
from portal.handlers import EventInfoHandler
from portal.route_classes import LogRoute
from portal.serializers.base import HeaderInfo
from portal.serializers.v1.event_info import EventScheduleList

router = APIRouter(
    route_class=LogRoute
)


@router.get(
    path="/{conference_id}/schedule",
    response_model=EventScheduleList,
    status_code=status.HTTP_200_OK,
)
@inject
async def get_event_schedule(
    conference_id: uuid.UUID,
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    event_info_handler: EventInfoHandler = Depends(Provide[Container.event_info_handler]),
) -> EventScheduleList:
    """
    Get event schedule
    :param conference_id:
    :param request:
    :param response:
    :param headers:
    :param event_info_handler:
    :return:
    """
    event_schedule_list = await event_info_handler.get_event_schedule(conference_id)
    return event_schedule_list

