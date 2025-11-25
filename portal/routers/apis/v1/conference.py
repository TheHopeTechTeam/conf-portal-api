"""
Conference API Router
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Request, Response, Depends
from fastapi.params import Header
from starlette import status

from portal.container import Container
from portal.handlers import ConferenceHandler
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.routers.auth_router import AuthRouter
from portal.serializers.base import HeaderInfo
from portal.serializers.v1.conference import ConferenceDetail, ConferenceList

router: AuthRouter = AuthRouter(
    require_auth=False,
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ]
)


@router.get(
    path="/list",
    response_model=ConferenceList,
    status_code=status.HTTP_200_OK,
    operation_id="get_conference_list",
)
@inject
async def get_conferences(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    conference_handler: ConferenceHandler = Depends(Provide[Container.conference_handler]),
) -> ConferenceList:
    """
    Get conference list
    :param request:
    :param response:
    :param headers:
    :param conference_handler:
    :return:
    """
    conference_list = await conference_handler.get_conferences()
    return conference_list


@router.get(
    path="/active",
    response_model=ConferenceDetail,
    status_code=status.HTTP_200_OK,
    operation_id="get_active_conference",
)
@inject
async def get_active_conference(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    conference_handler: ConferenceHandler = Depends(Provide[Container.conference_handler]),
) -> ConferenceDetail:
    """
    Get an active conference
    :param request:
    :param response:
    :param headers:
    :param conference_handler:
    :return:
    """
    conference = await conference_handler.get_active_conference()
    return conference


@router.get(
    path="/{conference_id}",
    response_model=ConferenceDetail,
    status_code=status.HTTP_200_OK,
    operation_id="get_conference_detail",
)
@inject
async def get_conference_detail(
    conference_id: uuid.UUID,
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    conference_handler: ConferenceHandler = Depends(Provide[Container.conference_handler]),
) -> ConferenceDetail:
    """
    Get conference detail
    :param conference_id:
    :param request:
    :param response:
    :param headers:
    :param conference_handler:
    :return:
    """
    conference_detail = await conference_handler.get_conference_detail(conference_id)
    return conference_detail
