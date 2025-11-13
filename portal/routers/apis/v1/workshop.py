"""
Workshop API Router
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Request, Response, Depends
from fastapi.params import Header
from starlette import status

from portal.container import Container
from portal.handlers import WorkshopHandler
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.routers.auth_router import AuthRouter
from portal.serializers.base import HeaderInfo
from portal.serializers.response_examples import workshop
from portal.serializers.v1.workshop import WorkshopDetail, WorkshopScheduleList, WorkshopRegisteredList

router: AuthRouter = AuthRouter(
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ]
)


@router.get(
    path="/schedules",
    response_model=WorkshopScheduleList,
    status_code=status.HTTP_200_OK,
    responses=workshop.WORKSHOP_LIST,
    require_auth=False
)
@inject
async def get_workshop_schedule_list(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    workshop_handler: WorkshopHandler = Depends(Provide[Container.workshop_handler]),
):
    """

    :param request:
    :param response:
    :param headers:
    :param workshop_handler:
    :return:
    """
    response.headers["Content-Language"] = headers.accept_language
    workshop_obj = await workshop_handler.get_workshop_schedule_list()
    return workshop_obj


@router.get(
    path="/my_workshops",
    status_code=status.HTTP_200_OK,
    response_model=WorkshopRegisteredList,
)
@inject
async def get_my_workshops(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    workshop_handler: WorkshopHandler = Depends(Provide[Container.workshop_handler]),
) -> WorkshopRegisteredList:
    """

    :param request:
    :param response:
    :param headers:
    :param workshop_handler:
    :return:
    """
    return await workshop_handler.get_my_workshops()


@router.get(
    path="/account/registered",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, bool],
    responses={
        status.HTTP_200_OK: {
            "description": "Get registered workshops",
            "content": {
                "application/json": {
                    "example": {
                        uuid.uuid4().hex: True,
                        uuid.uuid4().hex: False,
                        uuid.uuid4().hex: True,
                    }
                }
            }
        }
    }
)
@inject
async def get_registered_workshops(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    workshop_handler: WorkshopHandler = Depends(Provide[Container.workshop_handler]),
) -> dict[str, bool]:
    """

    :param request:
    :param response:
    :param headers:
    :param workshop_handler:
    :return:
    """
    return await workshop_handler.get_registered_workshops()


@router.get(
    path="/{workshop_id}",
    response_model=WorkshopDetail,
    status_code=status.HTTP_200_OK,
    require_auth=False
)
@inject
async def get_workshop_detail(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    workshop_id: uuid.UUID,
    workshop_handler: WorkshopHandler = Depends(Provide[Container.workshop_handler]),
) -> WorkshopDetail:
    """

    :param request:
    :param response:
    :param headers:
    :param workshop_id:
    :param workshop_handler:
    :return:
    """
    response.headers["Content-Language"] = headers.accept_language
    return await workshop_handler.get_workshop_detail(workshop_id=workshop_id)


@router.post(
    path="/{workshop_id}/register",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def register_workshop(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    workshop_id: uuid.UUID,
    workshop_handler: WorkshopHandler = Depends(Provide[Container.workshop_handler]),
) -> None:
    """

    :param request:
    :param response:
    :param headers:
    :param workshop_id:
    :param workshop_handler:
    :return:
    """
    await workshop_handler.register_workshop(workshop_id=workshop_id)


@router.post(
    path="/{workshop_id}/unregister",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def unregister_workshop(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    workshop_id: uuid.UUID,
    workshop_handler: WorkshopHandler = Depends(Provide[Container.workshop_handler]),
) -> None:
    """

    :param request:
    :param response:
    :param headers:
    :param workshop_id:
    :param workshop_handler:
    :return:
    """
    await workshop_handler.unregister_workshop(workshop_id=workshop_id)

