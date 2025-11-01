"""
Admin permission API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, status, Query

from portal.container import Container
from portal.handlers import AdminPermissionHandler
from portal.libs.depends import check_admin_access_token
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.v1.admin.permission import (
    PermissionPage,
    PermissionQuery,
    PermissionDetail,
    PermissionCreate,
    PermissionUpdate, PermissionBulkAction, PermissionList,
)

router = APIRouter(dependencies=[check_admin_access_token])


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=PermissionPage
)
@inject
async def get_permission_pages(
    query_model: Annotated[PermissionQuery, Query()],
    admin_permission_handler: AdminPermissionHandler = Depends(Provide[Container.admin_permission_handler])
):
    """
    Get permission pages
    :param query_model:
    :param admin_permission_handler:
    :return:
    """
    return await admin_permission_handler.get_permission_pages(model=query_model)

@router.get(
    path="/list",
    status_code=status.HTTP_200_OK,
    response_model=PermissionList
)
@inject
async def get_permission_list(
    admin_permission_handler: AdminPermissionHandler = Depends(Provide[Container.admin_permission_handler])
):
    """

    :param admin_permission_handler:
    :return:
    """
    return await admin_permission_handler.get_permission_list()


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel
)
@inject
async def create_permission(
    permission_data: PermissionCreate,
    admin_permission_handler: AdminPermissionHandler = Depends(Provide[Container.admin_permission_handler])
):
    """
    Create a permission
    :param permission_data:
    :param admin_permission_handler:
    :return:
    """
    return await admin_permission_handler.create_permission(model=permission_data)


@router.get(
    path="/{permission_id}",
    status_code=status.HTTP_200_OK,
    response_model=PermissionDetail
)
@inject
async def get_permission(
    permission_id: uuid.UUID,
    admin_permission_handler: AdminPermissionHandler = Depends(Provide[Container.admin_permission_handler])
):
    """
    Get a permission by ID
    :param permission_id:
    :param admin_permission_handler:
    :return:
    """
    return await admin_permission_handler.get_permission_by_id(permission_id=permission_id)


@router.put(
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def restore_permission(
    model: PermissionBulkAction,
    admin_permission_handler: AdminPermissionHandler = Depends(Provide[Container.admin_permission_handler])
):
    """
    Restore a permission
    :param model:
    :param admin_permission_handler:
    :return:
    """
    await admin_permission_handler.restore_permission(model=model)


@router.put(
    path="/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_permission(
    permission_id: uuid.UUID,
    permission_data: PermissionUpdate,
    admin_permission_handler: AdminPermissionHandler = Depends(Provide[Container.admin_permission_handler])
):
    """
    Update a permission
    :param permission_id:
    :param permission_data:
    :param admin_permission_handler:
    :return:
    """
    await admin_permission_handler.update_permission(permission_id=permission_id, model=permission_data)


@router.delete(
    path="/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def delete_permission(
    permission_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_permission_handler: AdminPermissionHandler = Depends(Provide[Container.admin_permission_handler])
):
    """
    Delete a permission
    :param permission_id:
    :param model:
    :param admin_permission_handler:
    :return:
    """
    await admin_permission_handler.delete_permission(permission_id=permission_id, model=model)
