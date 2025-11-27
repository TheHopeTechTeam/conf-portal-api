"""
Admin location API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminLocationHandler
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.location import (
    AdminLocationQuery,
    AdminLocationPages,
    AdminLocationDetail,
    AdminLocationCreate,
    AdminLocationUpdate, AdminLocationList,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=AdminLocationPages
)
@inject
async def get_location_pages(
    query_model: Annotated[AdminLocationQuery, Query()],
    admin_location_handler: AdminLocationHandler = Depends(Provide[Container.admin_location_handler])
):
    """
    Get location pages
    :param query_model:
    :param admin_location_handler:
    :return:
    """
    return await admin_location_handler.get_location_pages(model=query_model)


@router.get(
    path="/list",
    status_code=status.HTTP_200_OK,
    response_model=AdminLocationList
)
@inject
async def get_location_list(
    admin_location_handler: AdminLocationHandler = Depends(Provide[Container.admin_location_handler])
):
    """

    :param admin_location_handler:
    :return:
    """
    return await admin_location_handler.get_location_list()


@router.get(
    path="/{location_id}",
    status_code=status.HTTP_200_OK,
    response_model=AdminLocationDetail
)
@inject
async def get_location(
    location_id: uuid.UUID,
    admin_location_handler: AdminLocationHandler = Depends(Provide[Container.admin_location_handler])
):
    """
    Get a location by ID
    :param location_id:
    :param admin_location_handler:
    :return:
    """
    return await admin_location_handler.get_location_by_id(location_id=location_id)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel
)
@inject
async def create_location(
    location_data: AdminLocationCreate,
    admin_location_handler: AdminLocationHandler = Depends(Provide[Container.admin_location_handler])
):
    """
    Create a location
    :param location_data:
    :param admin_location_handler:
    :return:
    """
    return await admin_location_handler.create_location(model=location_data)


@router.put(
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def restore_locations(
    model: BulkAction,
    admin_location_handler: AdminLocationHandler = Depends(Provide[Container.admin_location_handler])
):
    """
    Restore soft-deleted locations
    :param model:
    :param admin_location_handler:
    :return:
    """
    await admin_location_handler.restore_locations(model=model)


@router.put(
    path="/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_location(
    location_id: uuid.UUID,
    location_data: AdminLocationUpdate,
    admin_location_handler: AdminLocationHandler = Depends(Provide[Container.admin_location_handler])
):
    """
    Update a location
    :param location_id:
    :param location_data:
    :param admin_location_handler:
    :return:
    """
    await admin_location_handler.update_location(location_id=location_id, model=location_data)


@router.delete(
    path="/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def delete_location(
    location_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_location_handler: AdminLocationHandler = Depends(Provide[Container.admin_location_handler])
):
    """
    Delete a location (soft by default)
    :param location_id:
    :param model:
    :param admin_location_handler:
    :return:
    """
    await admin_location_handler.delete_location(location_id=location_id, model=model)
