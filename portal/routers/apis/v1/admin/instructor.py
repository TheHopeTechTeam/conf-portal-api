"""
Admin instructor API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminInstructorHandler
from portal.libs.consts.permission import Permission
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.instructor import (
    AdminInstructorQuery,
    AdminInstructorPages,
    AdminInstructorDetail,
    AdminInstructorCreate,
    AdminInstructorUpdate, AdminInstructorList,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=AdminInstructorPages,
    permissions=[
        Permission.CONTENT_INSTRUCTOR.read
    ]
)
@inject
async def get_instructor_pages(
    query_model: Annotated[AdminInstructorQuery, Query()],
    admin_instructor_handler: AdminInstructorHandler = Depends(Provide[Container.admin_instructor_handler])
):
    """
    Get instructor pages
    :param query_model:
    :param admin_instructor_handler:
    :return:
    """
    return await admin_instructor_handler.get_instructor_pages(model=query_model)


@router.get(
    path="/list",
    status_code=status.HTTP_200_OK,
    response_model=AdminInstructorList,
    permissions=[
        Permission.CONTENT_INSTRUCTOR.read
    ]
)
@inject
async def get_instructor_list(
    admin_instructor_handler: AdminInstructorHandler = Depends(Provide[Container.admin_instructor_handler])
):
    """

    :param admin_instructor_handler:
    :return:
    """
    return await admin_instructor_handler.get_instructor_list()


@router.get(
    path="/{instructor_id}",
    status_code=status.HTTP_200_OK,
    response_model=AdminInstructorDetail,
    permissions=[
        Permission.CONTENT_INSTRUCTOR.read
    ]
)
@inject
async def get_instructor(
    instructor_id: uuid.UUID,
    admin_instructor_handler: AdminInstructorHandler = Depends(Provide[Container.admin_instructor_handler])
):
    """
    Get an instructor by ID
    :param instructor_id:
    :param admin_instructor_handler:
    :return:
    """
    return await admin_instructor_handler.get_instructor_by_id(instructor_id=instructor_id)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel,
    permissions=[
        Permission.CONTENT_INSTRUCTOR.create
    ]
)
@inject
async def create_instructor(
    instructor_data: AdminInstructorCreate,
    admin_instructor_handler: AdminInstructorHandler = Depends(Provide[Container.admin_instructor_handler])
):
    """
    Create an instructor
    :param instructor_data:
    :param admin_instructor_handler:
    :return:
    """
    return await admin_instructor_handler.create_instructor(model=instructor_data)


@router.put(
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT,
    permissions=[
        Permission.CONTENT_INSTRUCTOR.modify
    ]
)
@inject
async def restore_instructors(
    model: BulkAction,
    admin_instructor_handler: AdminInstructorHandler = Depends(Provide[Container.admin_instructor_handler])
):
    """
    Restore soft-deleted instructors
    :param model:
    :param admin_instructor_handler:
    :return:
    """
    await admin_instructor_handler.restore_instructors(model=model)


@router.put(
    path="/{instructor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    permissions=[
        Permission.CONTENT_INSTRUCTOR.modify
    ]
)
@inject
async def update_instructor(
    instructor_id: uuid.UUID,
    instructor_data: AdminInstructorUpdate,
    admin_instructor_handler: AdminInstructorHandler = Depends(Provide[Container.admin_instructor_handler])
):
    """
    Update an instructor
    :param instructor_id:
    :param instructor_data:
    :param admin_instructor_handler:
    :return:
    """
    await admin_instructor_handler.update_instructor(instructor_id=instructor_id, model=instructor_data)


@router.delete(
    path="/{instructor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    permissions=[
        Permission.CONTENT_INSTRUCTOR.delete
    ]
)
@inject
async def delete_instructor(
    instructor_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_instructor_handler: AdminInstructorHandler = Depends(Provide[Container.admin_instructor_handler])
):
    """
    Delete an instructor (soft by default)
    :param instructor_id:
    :param model:
    :param admin_instructor_handler:
    :return:
    """
    await admin_instructor_handler.delete_instructor(instructor_id=instructor_id, model=model)
