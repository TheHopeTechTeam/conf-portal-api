"""
Feedback API Router
"""

from dependency_injector.wiring import inject, Provide
from fastapi import Depends
from starlette import status

from portal.container import Container
from portal.handlers import FeedbackHandler
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.feedback import FeedbackCreate

router: AuthRouter = AuthRouter(
    require_auth=False,
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ]
)


@router.post(
    path="",
    response_model=UUIDBaseModel,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_feedback",
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
