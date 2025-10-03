"""
Admin user API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, Query, status

from portal.container import Container
from portal.handlers import AdminUserHandler
from portal.libs.depends import check_admin_access_token
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel, GenericQueryBaseModel
from portal.serializers.v1.admin.user import UserPages


router = APIRouter(dependencies=[check_admin_access_token])


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=UserPages
)
@inject
async def get_user_pages(
    query_model: Annotated[GenericQueryBaseModel, Query()],
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Get user pages
    :param query_model:
    :param admin_user_handler:
    :return:
    """
    return await admin_user_handler.get_user_pages(model=query_model)
