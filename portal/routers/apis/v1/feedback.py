"""
Feedback API Router
"""

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends
from starlette import status

from portal.container import Container
from portal.handlers import FeedbackHandler
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.route_classes import LogRoute
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.feedback import FeedbackCreate

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
async def create_feedback(
    model: FeedbackCreate,
    feedback_handler: FeedbackHandler = Depends(Provide[Container.feedback_handler]),
) -> UUIDBaseModel:
    """
    Create feedback
    :param model:
    :param feedback_handler:
    :return:
    """
    return await feedback_handler.creat_feedback(model)
