"""
Admin Workshop Registration API Router
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminWorkshopRegistrationHandler
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.v1.admin.workshop_registration import (
    AdminWorkshopRegistrationQuery,
    AdminWorkshopRegistrationPages,
    AdminWorkshopRegistrationDetail,
    AdminWorkshopRegistrationCreate,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=AdminWorkshopRegistrationPages,
)
@inject
async def get_workshop_registration_pages(
    query_model: Annotated[AdminWorkshopRegistrationQuery, Query()],
    admin_workshop_registration_handler: AdminWorkshopRegistrationHandler = Depends(Provide[Container.admin_workshop_registration_handler])
):
    """
    Get workshop registration pages
    :param query_model:
    :param admin_workshop_registration_handler:
    :return:
    """
    return await admin_workshop_registration_handler.get_workshop_registration_pages(query_model=query_model)


@router.get(
    path="/{registration_id}",
    status_code=status.HTTP_200_OK,
    response_model=AdminWorkshopRegistrationDetail,
)
@inject
async def get_workshop_registration_by_id(
    registration_id: uuid.UUID,
    admin_workshop_registration_handler: AdminWorkshopRegistrationHandler = Depends(Provide[Container.admin_workshop_registration_handler])
):
    """
    Get workshop registration by ID
    :param registration_id:
    :param admin_workshop_registration_handler:
    :return:
    """
    return await admin_workshop_registration_handler.get_workshop_registration_by_id(registration_id=registration_id)


@router.post(
    path="/",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel,
)
@inject
async def create_workshop_registration(
    model: AdminWorkshopRegistrationCreate,
    admin_workshop_registration_handler: AdminWorkshopRegistrationHandler = Depends(Provide[Container.admin_workshop_registration_handler])
):
    """
    Create a workshop registration
    :param model:
    :param admin_workshop_registration_handler:
    :return:
    """
    return await admin_workshop_registration_handler.create_workshop_registration(model=model)


@router.post(
    path="/{registration_id}/unregister",
    status_code=status.HTTP_204_NO_CONTENT,
)
@inject
async def unregister_workshop_registration(
    registration_id: uuid.UUID,
    admin_workshop_registration_handler: AdminWorkshopRegistrationHandler = Depends(Provide[Container.admin_workshop_registration_handler])
):
    """
    Unregister workshop registration
    :param registration_id:
    :param admin_workshop_registration_handler:
    :return:
    """
    return await admin_workshop_registration_handler.unregister_workshop_registration(registration_id=registration_id)


@router.delete(
    path="/{registration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@inject
async def delete_workshop_registration(
    registration_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_workshop_registration_handler: AdminWorkshopRegistrationHandler = Depends(Provide[Container.admin_workshop_registration_handler])
):
    """
    Delete workshop registration
    :param registration_id:
    :param model:
    :param admin_workshop_registration_handler:
    :return:
    """
    return await admin_workshop_registration_handler.delete_workshop_registration(registration_id=registration_id, model=model)

