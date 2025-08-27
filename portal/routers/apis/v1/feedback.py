"""
Feedback API Router
"""
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Request, Response, Depends
from fastapi.params import Header
from starlette import status

from portal.container import Container
from portal.handlers import FeedbackHandler
from portal.route_classes import LogRoute
from portal.serializers.base import HeaderInfo
from portal.serializers.v1.feedback import FeedbackCreate, FeedbackCreateResponse

router = APIRouter(
    route_class=LogRoute
)


@router.post(
    path="",
    response_model=FeedbackCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def create_feedback(
    request: Request,
    response: Response,
    headers: Annotated[HeaderInfo, Header()],
    model: FeedbackCreate,
    feedback_handler: FeedbackHandler = Depends(Provide[Container.feedback_handler]),
) -> FeedbackCreateResponse:
    """
    Create feedback
    :param request:
    :param response:
    :param headers:
    :param model:
    :param feedback_handler:
    :return:
    """
    feedback_create_response = await feedback_handler.creat_feedback(model)
    return feedback_create_response
