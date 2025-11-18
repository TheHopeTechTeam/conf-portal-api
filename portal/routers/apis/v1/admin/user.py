"""
Admin user API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminUserHandler
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.v1.admin.user import UserQuery, UserPages, UserCreate, UserItem, UserUpdate, UserBulkAction, BindRole, ChangePassword, UserRoles

router: AuthRouter = AuthRouter(is_admin=True)


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
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=UserItem
)
@inject
async def get_current_user(
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """

    :param admin_user_handler:
    :return:
    """
    return await admin_user_handler.get_current_user()


@router.get(
    path="/{user_id}/roles",
    status_code=status.HTTP_200_OK,
    description="Get user roles",
    response_model=UserRoles
)
@inject
async def get_user_roles(
    user_id: uuid.UUID,
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Get user roles
    :param user_id:
    :param admin_user_handler:
    :return:
    """
    return await admin_user_handler.get_user_roles(user_id=user_id)


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
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def restore_users(
    model: UserBulkAction,
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Restore soft-deleted users
    :param model:
    :param admin_user_handler:
    :return:
    """
    await admin_user_handler.restore_user(model=model)


@router.post(
    path="/{user_id}/bind_role",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def bind_roles_to_user(
    user_id: uuid.UUID,
    model: BindRole,
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """
    Bind roles to user
    :param user_id:
    :param model:
    :param admin_user_handler:
    :return:
    """
    await admin_user_handler.bind_roles(user_id=user_id, model=model)


@router.post(
    path="/{user_id}/change_password",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def change_user_password(
    user_id: uuid.UUID,
    model: ChangePassword,
    admin_user_handler: AdminUserHandler = Depends(Provide[Container.admin_user_handler])
):
    """

    :param user_id:
    :param model:
    :param admin_user_handler:
    :return:
    """
    await admin_user_handler.change_password(user_id=user_id, model=model)


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
