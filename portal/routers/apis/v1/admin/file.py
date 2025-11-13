"""
Admin file API routes
"""
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import UploadFile, Depends, status, Query

from portal.container import Container
from portal.handlers import AdminFileHandler
from portal.libs.consts.enums import FileUploadSource
from portal.libs.depends.file_validation import FileValidation
from portal.routers.auth_router import AuthRouter
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.file import FileUploadResponseModel, FilePages, FileQuery, BulkActionResponseModel

router: AuthRouter = AuthRouter(is_admin=True)

ALLOWED_TYPES = [
    "image/apng",  # Animated Portable Network Graphics (APNG)
    "image/avif",  # AV1 Image File Format (AVIF)
    "image/gif",  # Graphics Interchange Format (GIF)
    "image/jpeg",  # Joint Photographic Expert Group image (JPEG)
    "image/png",  # Portable Network Graphics (PNG)
    "image/svg+xml",  # Scalable Vector Graphics (SVG)
    "image/webp",  # Web Picture format (WEBP)
]


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=FilePages
)
@inject
async def get_file_pages(
    query_model: Annotated[FileQuery, Query()],
    admin_file_handler: AdminFileHandler = Depends(Provide[Container.admin_file_handler])
):
    """

    :param query_model:
    :param admin_file_handler:
    :return:
    """
    return await admin_file_handler.get_file_pages(model=query_model)


@router.post(
    path="/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=FileUploadResponseModel,
    response_model_exclude_none=True,
)
@inject
async def upload_file(
    file: UploadFile = Depends(FileValidation(allowed_types=ALLOWED_TYPES)),
    file_handler: AdminFileHandler = Depends(Provide[Container.admin_file_handler])
):
    """

    :param file:
    :param file_handler:
    :return:
    """
    return await file_handler.upload_file(upload_file=file, upload_source=FileUploadSource.ADMIN)


@router.post(
    path="/batch_upload",
    status_code=status.HTTP_201_CREATED,
)
@inject
async def upload_multiple_files(
    files: list[UploadFile],
    file_handler: AdminFileHandler = Depends(Provide[Container.admin_file_handler])
):
    """

    :param files:
    :param file_handler:
    :return:
    """
    return await file_handler.upload_multiple_files(upload_files=files, upload_source=FileUploadSource.ADMIN)


@router.delete(
    path="/bulk",
    status_code=status.HTTP_200_OK,
    description="For deleting files",
    response_model=BulkActionResponseModel,
)
@inject
async def delete_files(
    model: BulkAction,
    admin_file_handler: AdminFileHandler = Depends(Provide[Container.admin_file_handler])
):
    """

    :param model:
    :param admin_file_handler:
    :return:
    """
    return await admin_file_handler.delete_files(model=model)
