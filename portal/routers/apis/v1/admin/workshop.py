"""
Admin Workshop API Router
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminWorkshopHandler
from portal.libs.consts.permission import Permission
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.workshop import (
    AdminWorkshopQuery,
    AdminWorkshopDetail,
    AdminWorkshopPages,
    AdminWorkshopCreate,
    AdminWorkshopUpdate,
    AdminWorkshopChangeSequence,
    AdminWorkshopInstructorsUpdate,
    AdminWorkshopInstructors,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=AdminWorkshopPages,
    permissions=[
        Permission.WORKSHOP_WORKSHOPS.read
    ]
)
@inject
async def get_workshop_pages(
    query_model: Annotated[AdminWorkshopQuery, Query()],
    admin_workshop_handler: AdminWorkshopHandler = Depends(Provide[Container.admin_workshop_handler])
):
    """
    Get workshop pages
    :param query_model:
    :param admin_workshop_handler:
    :return:
    """
    return await admin_workshop_handler.get_workshop_pages(query_model=query_model)


@router.get(
    path="/{workshop_id}",
    status_code=status.HTTP_200_OK,
    response_model=AdminWorkshopDetail,
    permissions=[
        Permission.WORKSHOP_WORKSHOPS.read
    ]
)
@inject
async def get_workshop_by_id(
    workshop_id: uuid.UUID,
    admin_workshop_handler: AdminWorkshopHandler = Depends(Provide[Container.admin_workshop_handler])
):
    """
    Get workshop by ID
    :param workshop_id:
    :param admin_workshop_handler:
    :return:
    """
    return await admin_workshop_handler.get_workshop_by_id(workshop_id=workshop_id)


@router.post(
    path="/",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel,
    permissions=[
        Permission.WORKSHOP_WORKSHOPS.create
    ]
)
@inject
async def create_workshop(
    model: AdminWorkshopCreate,
    admin_workshop_handler: AdminWorkshopHandler = Depends(Provide[Container.admin_workshop_handler])
):
    """
    Create a workshop
    :param model:
    :param admin_workshop_handler:
    :return:
    """
    return await admin_workshop_handler.create_workshop(model=model)


@router.put(
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    permissions=[
        Permission.WORKSHOP_WORKSHOPS.modify
    ]
)
@inject
async def restore_workshops(
    model: BulkAction,
    admin_workshop_handler: AdminWorkshopHandler = Depends(Provide[Container.admin_workshop_handler])
):
    """
    Restore workshops
    :param model:
    :param admin_workshop_handler:
    :return:
    """
    return await admin_workshop_handler.restore_workshops(model=model)


@router.put(
    path="/{workshop_id}",
    status_code=status.HTTP_200_OK,
    response_model=None,
    permissions=[
        Permission.WORKSHOP_WORKSHOPS.modify
    ]
)
@inject
async def update_workshop(
    workshop_id: uuid.UUID,
    model: AdminWorkshopUpdate,
    admin_workshop_handler: AdminWorkshopHandler = Depends(Provide[Container.admin_workshop_handler])
):
    """
    Update a workshop
    :param workshop_id:
    :param model:
    :param admin_workshop_handler:
    :return:
    """
    return await admin_workshop_handler.update_workshop(workshop_id=workshop_id, model=model)


@router.delete(
    path="/{workshop_id}",
    status_code=status.HTTP_200_OK,
    response_model=None,
    permissions=[
        Permission.WORKSHOP_WORKSHOPS.delete
    ]
)
@inject
async def delete_workshop(
    workshop_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_workshop_handler: AdminWorkshopHandler = Depends(Provide[Container.admin_workshop_handler])
):
    """
    Delete a workshop
    :param workshop_id:
    :param model:
    :param admin_workshop_handler:
    :return:
    """
    return await admin_workshop_handler.delete_workshop(workshop_id=workshop_id, model=model)


@router.put(
    path="/{workshop_id}/sequence",
    status_code=status.HTTP_200_OK,
    response_model=None,
    permissions=[
        Permission.WORKSHOP_WORKSHOPS.modify
    ]
)
@inject
async def change_sequence(
    model: AdminWorkshopChangeSequence,
    admin_workshop_handler: AdminWorkshopHandler = Depends(Provide[Container.admin_workshop_handler])
):
    """
    Change sequence of a workshop
    :param model:
    :param admin_workshop_handler:
    :return:
    """
    return await admin_workshop_handler.change_sequence(model=model)


@router.get(
    path="/instructors/{workshop_id}",
    status_code=status.HTTP_200_OK,
    response_model=AdminWorkshopInstructors,
    permissions=[
        Permission.WORKSHOP_WORKSHOPS.read
    ]
)
@inject
async def get_workshop_instructors(
    workshop_id: uuid.UUID,
    admin_workshop_handler: AdminWorkshopHandler = Depends(Provide[Container.admin_workshop_handler])
):
    """
    Get workshop instructors
    :param workshop_id:
    :param admin_workshop_handler:
    :return:
    """
    return await admin_workshop_handler.get_workshop_instructors(workshop_id=workshop_id)


@router.put(
    path="/instructors/{workshop_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    permissions=[
        Permission.WORKSHOP_WORKSHOPS.modify
    ]
)
@inject
async def update_workshop_instructors(
    workshop_id: uuid.UUID,
    model: AdminWorkshopInstructorsUpdate,
    admin_workshop_handler: AdminWorkshopHandler = Depends(Provide[Container.admin_workshop_handler])
):
    """
    Update workshop instructors
    :param workshop_id:
    :param model:
    :param admin_workshop_handler:
    :return:
    """
    return await admin_workshop_handler.update_workshop_instructors(workshop_id=workshop_id, model=model)
