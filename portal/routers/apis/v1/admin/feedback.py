"""
Admin feedback API routes
"""
from typing import Annotated
import uuid

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, Query, status

from portal.container import Container
from portal.handlers import AdminFeedbackHandler
from portal.libs.depends import check_admin_access_token
from portal.route_classes import LogRoute
from portal.serializers.v1.admin.feedback import (
    FeedbackQuery,
    FeedbackPages,
    FeedbackDetail,
    FeedbackUpdate,
)

router = APIRouter(route_class=LogRoute, dependencies=[check_admin_access_token])


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=FeedbackPages
)
@inject
async def get_feedback_pages(
    query_model: Annotated[FeedbackQuery, Query()],
    admin_feedback_handler: AdminFeedbackHandler = Depends(Provide[Container.admin_feedback_handler])
):
    return await admin_feedback_handler.get_feedback_pages(model=query_model)


@router.get(
    path="/{feedback_id}",
    status_code=status.HTTP_200_OK,
    response_model=FeedbackDetail
)
@inject
async def get_feedback(
    feedback_id: uuid.UUID,
    admin_feedback_handler: AdminFeedbackHandler = Depends(Provide[Container.admin_feedback_handler])
):
    return await admin_feedback_handler.get_feedback_by_id(feedback_id=str(feedback_id))


@router.put(
    path="/{feedback_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_feedback(
    feedback_id: uuid.UUID,
    body: FeedbackUpdate,
    admin_feedback_handler: AdminFeedbackHandler = Depends(Provide[Container.admin_feedback_handler])
):
    await admin_feedback_handler.update_feedback(feedback_id=feedback_id, model=body)
