"""
Admin conference API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminConferenceHandler
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.conference import (
    ConferenceQuery,
    ConferencePages,
    ConferenceDetail,
    ConferenceCreate,
    ConferenceUpdate,
    ConferenceInstructorsUpdate, ConferenceItem, ConferenceList, ConferenceInstructors,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=ConferencePages,
)
@inject
async def get_conference_pages(
    query_model: Annotated[ConferenceQuery, Query()],
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """
    Get conference pages
    :param query_model:
    :param admin_conference_handler:
    :return:
    """
    return await admin_conference_handler.get_conference_pages(model=query_model)


@router.get(
    path="/list",
    status_code=status.HTTP_200_OK,
    response_model=ConferenceList
)
@inject
async def get_conference_list(
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """

    :param admin_conference_handler:
    :return:
    """
    return await admin_conference_handler.get_conference_list()


@router.get(
    path="/active",
    status_code=status.HTTP_200_OK,
    response_model=ConferenceItem
)
@inject
async def get_active_conference(
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """

    :param admin_conference_handler:
    :return:
    """
    return await admin_conference_handler.get_active_conference()


@router.get(
    path="/{conference_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConferenceDetail
)
@inject
async def get_conference(
    conference_id: uuid.UUID,
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """
    Get a conference by ID
    :param conference_id:
    :param admin_conference_handler:
    :return:
    """
    return await admin_conference_handler.get_conference_by_id(conference_id=conference_id)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel
)
@inject
async def create_conference(
    conference_data: ConferenceCreate,
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """
    Create a conference
    :param conference_data:
    :param admin_conference_handler:
    :return:
    """
    return await admin_conference_handler.create_conference(model=conference_data)


@router.put(
    path="/{conference_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_conference(
    conference_id: uuid.UUID,
    conference_data: ConferenceUpdate,
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """
    Update a conference
    :param conference_id:
    :param conference_data:
    :param admin_conference_handler:
    :return:
    """
    await admin_conference_handler.update_conference(conference_id=conference_id, model=conference_data)


@router.get(
    path="/instructors/{conference_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConferenceInstructors
)
@inject
async def get_conference_instructors(
    conference_id: uuid.UUID,
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """
    Get conference instructors mapping
    :param conference_id:
    :param admin_conference_handler:
    :return:
    """
    return await admin_conference_handler.get_conference_instructors(conference_id=conference_id)


@router.put(
    path="/instructors/{conference_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_conference_instructors(
    conference_id: uuid.UUID,
    body: ConferenceInstructorsUpdate,
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """
    Update conference instructors mapping
    :param conference_id:
    :param body:
    :param admin_conference_handler:
    :return:
    """
    await admin_conference_handler.update_conference_instructors(conference_id=conference_id, model=body)


@router.delete(
    path="/{conference_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def delete_conference(
    conference_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """
    Delete a conference (soft by default)
    :param conference_id:
    :param model:
    :param admin_conference_handler:
    :return:
    """
    await admin_conference_handler.delete_conference(conference_id=conference_id, model=model)


@router.put(
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def restore_conferences(
    model: BulkAction,
    admin_conference_handler: AdminConferenceHandler = Depends(Provide[Container.admin_conference_handler])
):
    """
    Restore soft-deleted conferences
    :param model:
    :param admin_conference_handler:
    :return:
    """
    await admin_conference_handler.restore_conferences(model=model)
