"""
Admin user API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, Query, status, Request

from portal.container import Container
from portal.handlers import AdminUserHandler
from portal.libs.depends import check_admin_access_token
from portal.route_classes import LogRoute
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.v1.admin.user import UserQuery, UserPages, UserCreate, UserItem, UserUpdate, UserBulkDelete

router = APIRouter(route_class=LogRoute, dependencies=[check_admin_access_token])


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=UserPages
)
@inject
async def get_user_pages(
    query_model: Annotated[UserQuery, Query()],
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Get user pages
    :param query_model:
    :param admin_user_handler:
    :return:
    """
    return await admin_user_handler.get_user_pages(model=query_model)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel
)
@inject
async def create_user(
    user_data: UserCreate,
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Create a user
    :param user_data:
    :param admin_user_handler:
    :return:
    """
    return await admin_user_handler.create_user(model=user_data)


@router.get(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserItem
)
@inject
async def get_user(
    user_id: uuid.UUID,
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Get a user by ID
    :param user_id:
    :param admin_user_handler:
    :return:
    """
    user = await admin_user_handler.get_user_by_id(user_id=user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put(
    path="/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Update a user
    :param user_id:
    :param user_data:
    :param admin_user_handler:
    :return:
    """
    await admin_user_handler.update_user(user_id=user_id, model=user_data)


@router.delete(
    path="/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def delete_user(
    user_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Delete a user (soft by default)
    :param user_id:
    :param model:
    :param admin_user_handler:
    :return:
    """
    await admin_user_handler.delete_user(user_id=user_id, model=model)


@router.put(
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def restore_users(
    model: UserBulkDelete,
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Restore soft-deleted users
    :param model:
    :param admin_user_handler:
    :return:
    """
    await admin_user_handler.restore_user(user_ids=model.ids)
