"""
Event Info API Router
"""
import uuid

from dependency_injector.wiring import inject, Provide
from fastapi import Depends
from starlette import status

from portal.container import Container
from portal.handlers import EventInfoHandler
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.routers.auth_router import AuthRouter
from portal.serializers.v1.event_info import EventScheduleList

router: AuthRouter = AuthRouter(
    require_auth=False,
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ]
)

@router.get(
    path="/{conference_id}/schedule",
    response_model=EventScheduleList,
    status_code=status.HTTP_200_OK,
    operation_id="get_event_schedule",
)
@inject
async def get_event_schedule(
    conference_id: uuid.UUID,
    event_info_handler: EventInfoHandler = Depends(Provide[Container.event_info_handler]),
) -> EventScheduleList:
    """
    Get event schedule
    :param conference_id:
    :param event_info_handler:
    :return:
    """
    return await event_info_handler.get_event_schedule(conference_id)
