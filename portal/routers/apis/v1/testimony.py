"""
Testimony API Router
"""
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Request, Response, Depends
from fastapi.params import Header
from starlette import status

from portal.container import Container
from portal.handlers import TestimonyHandler
from portal.route_classes import LogRoute
from portal.serializers.base import HeaderInfo
from portal.serializers.v1.testimony import TestimonyCreate, TestimonyCreateResponse

router = APIRouter(
    route_class=LogRoute
)


@router.post(
    path="",
    response_model=TestimonyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def create_testimony(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    model: TestimonyCreate,
    testimony_handler: TestimonyHandler = Depends(Provide[Container.testimony_handler]),
) -> TestimonyCreateResponse:
    """
    Create testimony
    :param request:
    :param response:
    :param headers:
    :param model:
    :param testimony_handler:
    :return:
    """
    testimony_create_response = await testimony_handler.create_testimony(model)
    return testimony_create_response
