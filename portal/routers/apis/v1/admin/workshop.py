"""
Admin Workshop API Router
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminWorkshopHandler
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.workshop import (
    WorkshopQuery,
    WorkshopDetail,
    WorkshopPages,
    WorkshopCreate,
    WorkshopUpdate,
    WorkshopChangeSequence,
    WorkshopInstructorsUpdate,
    WorkshopInstructors,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=WorkshopPages,
)
@inject
async def get_workshop_pages(
    query_model: Annotated[WorkshopQuery, Query()],
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
    response_model=WorkshopDetail,
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
)
@inject
async def create_workshop(
    model: WorkshopCreate,
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
    path="/{workshop_id}",
    status_code=status.HTTP_200_OK,
    response_model=None,
)
@inject
async def update_workshop(
    workshop_id: uuid.UUID,
    model: WorkshopUpdate,
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
)
@inject
async def change_sequence(
    model: WorkshopChangeSequence,
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
    response_model=WorkshopInstructors,
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
)
@inject
async def update_workshop_instructors(
    workshop_id: uuid.UUID,
    model: WorkshopInstructorsUpdate,
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


@router.put(
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
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
