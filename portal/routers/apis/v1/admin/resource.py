"""
Admin resource API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, status, Query

from portal.container import Container
from portal.handlers import AdminResourceHandler
from portal.libs.depends import check_admin_access_token
from portal.route_classes import LogRoute
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import DeleteQueryBaseModel
from portal.serializers.v1.admin.resource import (
    ResourceCreate,
    ResourceUpdate,
    ResourceChangeSequence,
    ResourceList, ResourceDetail, ResourceChangeParent,
)

router = APIRouter(route_class=LogRoute, dependencies=[check_admin_access_token])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel
)
@inject
async def create_resource(
    resource_data: ResourceCreate,
    admin_resource_handler: AdminResourceHandler = Depends(Provide[Container.admin_resource_handler])
):
    """

    :param resource_data:
    :param admin_resource_handler:
    :return:
    """
    return await admin_resource_handler.create_resource(model=resource_data)


@router.delete(
    path="/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def delete_resource(
    resource_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_resource_handler: AdminResourceHandler = Depends(Provide[Container.admin_resource_handler])
):
    """

    :param resource_id:
    :param model:
    :param admin_resource_handler:
    :return:
    """
    await admin_resource_handler.delete_resource(resource_id=resource_id, model=model)


@router.put(
    path="/restore/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def restore_resource(
    resource_id: uuid.UUID,
    admin_resource_handler: AdminResourceHandler = Depends(Provide[Container.admin_resource_handler])
):
    """

    :param resource_id:
    :param admin_resource_handler:
    :return:
    """
    await admin_resource_handler.restore_resource(resource_id=resource_id)


@router.put(
    path="/change_parent/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def change_resource_parent(
    resource_id: uuid.UUID,
    model: ResourceChangeParent,
    admin_resource_handler: AdminResourceHandler = Depends(Provide[Container.admin_resource_handler])
):
    """

    :param resource_id:
    :param model:
    :param admin_resource_handler:
    :return:
    """
    await admin_resource_handler.change_parent(resource_id=resource_id, model=model)


@router.put(
    path="/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_resource(
    resource_id: uuid.UUID,
    resource_data: ResourceUpdate,
    admin_resource_handler: AdminResourceHandler = Depends(Provide[Container.admin_resource_handler])
):
    """

    :param resource_id:
    :param resource_data:
    :param admin_resource_handler:
    :return:
    """
    await admin_resource_handler.update_resource(resource_id=resource_id, model=resource_data)


@router.post(
    path="/change_sequence",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def change_resource_sequence(
    model: ResourceChangeSequence,
    admin_resource_handler: AdminResourceHandler = Depends(Provide[Container.admin_resource_handler])
):
    """

    :param model:
    :param admin_resource_handler:
    :return:
    """
    await admin_resource_handler.change_sequence(model=model)


@router.get(
    "/list",
    status_code=status.HTTP_200_OK,
    response_model=ResourceList
)
@inject
async def get_resources(
    query_model: Annotated[DeleteQueryBaseModel, Query()],
    admin_resource_handler: AdminResourceHandler = Depends(Provide[Container.admin_resource_handler])
):
    """
    Get resources
    :param query_model:
    :param admin_resource_handler:
    :return:
    """
    return await admin_resource_handler.get_resources(query_model)


@router.get(
    path="/menus",
    status_code=status.HTTP_200_OK,
    response_model=ResourceList
)
@inject
async def get_menus(
    admin_resource_handler: AdminResourceHandler = Depends(Provide[Container.admin_resource_handler])
):
    """
    Get menus
    :param admin_resource_handler:
    :return:
    """
    return await admin_resource_handler.get_user_permission_menus()


@router.get(
    path="/{resource_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResourceDetail
)
@inject
async def get_resource(
    resource_id: uuid.UUID,
    admin_resource_handler: AdminResourceHandler = Depends(Provide[Container.admin_resource_handler])
):
    """

    :param resource_id:
    :param admin_resource_handler:
    :return:
    """
    return await admin_resource_handler.get_resource(resource_id=resource_id)
