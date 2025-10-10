"""
Admin file API routes
"""
import uuid
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, UploadFile, Depends, status

from portal.container import Container
from portal.handlers.file import FileHandler
from portal.libs.consts.enums import FileUploadSource
from portal.libs.depends.authenticators import check_access_token
from portal.libs.depends.file_validation import FileValidation
from portal.serializers.v1.file import FileUploadResponseModel

router = APIRouter()

ALLOWED_TYPES = [
    "image/apng",  # Animated Portable Network Graphics (APNG)
    "image/avif",  # AV1 Image File Format (AVIF)
    "image/gif",  # Graphics Interchange Format (GIF)
    "image/jpeg",  # Joint Photographic Expert Group image (JPEG)
    "image/png",  # Portable Network Graphics (PNG)
    "image/svg+xml",  # Scalable Vector Graphics (SVG)
    "image/webp",  # Web Picture format (WEBP)
]


@router.post(
    path="/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=FileUploadResponseModel,
    response_model_exclude_none=True,
)
@inject
async def upload_file(
    file: UploadFile = Depends(FileValidation(allowed_types=ALLOWED_TYPES)),
    file_handler: FileHandler = Depends(Provide[Container.file_handler])
):
    """

    :param file:
    :param file_handler:
    :return:
    """
    return await file_handler.upload_file(upload_file=file, upload_source=FileUploadSource.ADMIN)

# @router.post(
#     path="/batch_upload",
#     status_code=status.HTTP_201_CREATED,
# )
# @inject
# async def upload_multiple_files(
#     files: list[UploadFile],
#     file_handler: FileHandler = Depends(Provide[Container.file_handler])
# ):
#     """
#
#     :param files:
#     :param file_handler:
#     :return:
#     """
#     return await file_handler.upload_multiple_files(upload_files=files, upload_source=FileUploadSource.ADMIN)


@router.delete(
    path="/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[check_access_token],
    description="For deleting an file"
)
@inject
async def delete_file(
    file_id: uuid.UUID,
    file_handler: FileHandler = Depends(Provide[Container.file_handler])
):
    """
    Delete a file
    """
    await file_handler.delete_file(file_id=file_id)
