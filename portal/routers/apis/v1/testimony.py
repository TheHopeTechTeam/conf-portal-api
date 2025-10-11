"""
Testimony API Router
"""

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends
from starlette import status

from portal.container import Container
from portal.handlers import TestimonyHandler
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.route_classes import LogRoute
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.testimony import TestimonyCreate

router = APIRouter(
    route_class=LogRoute,
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ]
)


@router.post(
    path="",
    response_model=UUIDBaseModel,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def create_testimony(
    model: TestimonyCreate,
    testimony_handler: TestimonyHandler = Depends(Provide[Container.testimony_handler]),
) -> UUIDBaseModel:
    """
    Create testimony
    :param model:
    :param testimony_handler:
    :return:
    """
    return await testimony_handler.create_testimony(model)
