"""
AdminFileHandler
"""
import asyncio
import hashlib
import io
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional

import boto3
from PIL import Image
from asyncpg import UniqueViolationError
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import UploadFile, status
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import BadRequestException, ApiBaseException, ConflictErrorException
from portal.libs.consts.cache_keys import CacheKeys, CacheExpiry
from portal.libs.consts.enums import FileStatus, FileUploadSource
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.models import PortalFile, PortalFileAssociation
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.file import (
    BatchFileUploadResponseModel,
    FailedUploadFile,
    FileDetail,
    FileUploadResponseModel,
    FileQuery,
    FileGridItem,
    FilePages, FileBase, BulkActionResponseModel,
)


class AdminFileHandler:
    """
    FileHandler for AWS S3 operations and file management
    refer to: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
    """

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_S3_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self._bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self._folder_prefix = "original_files"

    @distributed_trace()
    async def get_file_pages(self, model: FileQuery) -> FilePages:
        """
        List files
        :return:
        """
        file_items, count = await (
            self._session.select(
                PortalFile.id,
                PortalFile.original_name,
                PortalFile.key,
                PortalFile.storage,
                PortalFile.bucket,
                PortalFile.region,
                PortalFile.content_type,
                PortalFile.extension,
                PortalFile.size_bytes
            )
            .where(PortalFile.status != FileStatus.DELETED)
            .where(
                model.keyword, lambda: PortalFile.original_name.ilike(f"%{model.keyword}%")
            )
            .order_by_with(
                tables=[PortalFile],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=FileGridItem
            )
        )  # type: (list[FileGridItem], int)

        tasks = []
        for file in file_items:
            tasks.append(self.get_signed_url(file=file))

        signed_urls = await asyncio.gather(*tasks)
        for file, signed_url in zip(file_items, signed_urls):  # type: (FileGridItem, Optional[str])
            file.url = signed_url

        return FilePages(
            total=count,
            items=file_items,
            page=model.page,
            page_size=model.page_size,
        )

    @distributed_trace()
    async def upload_file(
        self,
        upload_file: UploadFile,
        upload_source: FileUploadSource,
        is_public: bool = False,
        check_duplicates: bool = True
    ) -> FileUploadResponseModel:
        """
        Upload file to AWS S3 and store metadata in database

        :param upload_file:
        :param is_public: Whether the file should be publicly accessible
        :param upload_source: Source of the upload (admin: 0, app: 1)
        :param check_duplicates: Whether to check for duplicate files
        :return: PortalFile instance
        """
        try:
            # Read file content from UploadFile
            file_content = await upload_file.read()
            original_filename = upload_file.filename or "unknown_file"
            content_type = upload_file.content_type

            # Detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(original_filename)
                if not content_type:
                    content_type = "application/octet-stream"

            # Extract file metadata
            file_size = len(file_content)
            width, height = None, None

            # Extract image dimensions if it's an image
            if content_type.startswith("image/"):
                try:
                    with Image.open(io.BytesIO(file_content)) as img:
                        width, height = img.size
                except Exception:
                    pass  # Ignore if we can't extract image dimensions

            # Check for duplicate files if requested
            if check_duplicates:
                existing_file = await self.check_duplicate_by_multiple_checksums(
                    file_content=file_content,
                    content_type=content_type,
                    file_size=file_size
                )
                if existing_file:
                    # Return existing file ID instead of creating a new one
                    return FileUploadResponseModel(
                        id=existing_file.id,
                        duplicate=True
                    )

            # Calculate checksums
            md5_hash = hashlib.md5(file_content).hexdigest()
            sha256_hash = hashlib.sha256(file_content).hexdigest()

            # Generate unique key for S3
            file_id = uuid.uuid4()
            file_extension = Path(original_filename).suffix.lower()
            unique_filename = f"{file_id}{file_extension}"
            s3_key = os.path.join(self._folder_prefix, unique_filename)

            # Create database record first
            file_data = {
                "id": file_id,
                "original_name": original_filename,
                "key": s3_key,
                "storage": "s3",
                "bucket": self._bucket_name,
                "region": settings.AWS_S3_REGION_NAME,
                "content_type": content_type,
                "extension": file_extension.lstrip('.'),
                "size_bytes": file_size,
                "checksum_md5": md5_hash,
                "checksum_sha256": sha256_hash,
                "width": width,
                "height": height,
                "status": FileStatus.UPLOADING,
                "is_public": is_public,
                "source": upload_source
            }

            await (
                self._session.insert(PortalFile)
                .values(**file_data)
                .on_conflict_do_nothing(index_elements=["key", "bucket"])
                .execute()
            )

            response = self._s3_client.put_object(
                Body=file_content,
                Bucket=self._bucket_name,
                Key=s3_key,
                ContentType=content_type,
                Metadata={
                    "original-name": original_filename,
                    "file-id": file_id.hex,
                    "upload-source": str(upload_source.value),
                },
                CacheControl=settings.AWS_S3_CACHE_CONTROL,
            )
            print(response)

            # Update status to uploaded
            await (
                self._session.update(PortalFile)
                .values(status=FileStatus.UPLOADED)
                .where(PortalFile.id == file_id)
                .execute()
            )
        except (ClientError, NoCredentialsError) as e:
            raise ApiBaseException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AWS S3 service unavailable",
                debug_detail=str(e)
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail="File already exists",
                debug_detail=str(e)
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File upload failed",
                debug_detail=str(e)
            )
        else:
            return FileUploadResponseModel(id=file_id)

    @distributed_trace()
    async def upload_multiple_files(
        self,
        upload_files: list[UploadFile],
        upload_source: FileUploadSource,
        is_public: bool = False,
    ):
        """
        Upload multiple files to AWS S3 and store metadata in database

        :param upload_files: List of FastAPI UploadFile objects
        :param is_public: Whether the files should be publicly accessible
        :param upload_source: Source of the upload (admin, app)
        :return: List of PortalFile instances
        """
        uploaded_files = []
        failed_files = []

        for upload_file in upload_files:
            try:
                file_id: UUIDBaseModel = await self.upload_file(
                    upload_file=upload_file,
                    upload_source=upload_source,
                    is_public=is_public
                )
                uploaded_files.append(file_id)
            except Exception as e:
                failed_files.append(FailedUploadFile(filename=upload_file.filename, error=str(e)))

        return BatchFileUploadResponseModel(
            uploaded_files=uploaded_files,
            failed_files=failed_files
        )

    @distributed_trace()
    async def get_signed_url_by_resource_id(self, resource_id: uuid.UUID) -> Optional[list[str]]:
        """
        Generate a signed URL for file access by resource ID
        :param resource_id: Associated resource ID
        :return:
        """
        files: Optional[list[FileDetail]] = await (
            self._session.select(
                PortalFile.id,
                PortalFile.original_name,
                PortalFile.key,
                PortalFile.storage,
                PortalFile.bucket,
                PortalFile.region
            )
            .outerjoin(PortalFileAssociation, PortalFileAssociation.file_id == PortalFile.id)
            .where(PortalFile.is_public == True)
            .where(PortalFileAssociation.resource_id.isnot(None))
            .where(PortalFileAssociation.resource_id == resource_id)
            .fetch(as_model=FileDetail)
        )
        if not files:
            return None
        signed_urls = []
        for file in files:
            signed_url = await self.get_signed_url(file=file)
            signed_urls.append(signed_url)
        return signed_urls

    @distributed_trace()
    async def get_signed_url(self, file_id: uuid.UUID = None, file: FileBase = None, expiration: int = 3600) -> Optional[str]:
        """
        Generate a signed URL for file access
        :param file_id:
        :param file:
        :param expiration:
        :return:
        """
        try:
            if not file:
                file = await self.get_file_info(file_id)
            if not file:
                return None

            cache_key = CacheKeys("file").add_attribute("signed_url").add_attribute(file.id.hex).build()
            cached_url = await self._redis.get(cache_key)
            if cached_url:
                return cached_url

            url = self._s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": file.bucket,
                    "Key": file.key,
                },
                ExpiresIn=expiration
            )
            await self._redis.set(cache_key, url, ex=CacheExpiry.HOUR)
            return url

        except Exception as e:
            raise Exception(f"Failed to generate signed URL: {str(e)}")

    @distributed_trace()
    async def check_duplicate_file(
        self,
        file_content: bytes,
        checksum_sha256: Optional[str] = None
    ) -> Optional[FileDetail]:
        """
        Check if a file with the same content already exists

        :param file_content: File content bytes
        :param checksum_sha256: Pre-calculated SHA-256 checksum (optional)
        :return: Existing file if found, None otherwise
        """
        # Calculate SHA-256 if not provided
        if not checksum_sha256:
            checksum_sha256 = hashlib.sha256(file_content).hexdigest()

        # Check for existing file with same SHA-256 checksum
        existing_file: Optional[FileDetail] = await (
            self._session.select(
                PortalFile.id,
                PortalFile.original_name,
                PortalFile.key,
                PortalFile.storage,
                PortalFile.bucket,
                PortalFile.region,
                PortalFile.content_type,
                PortalFile.extension,
                PortalFile.size_bytes,
                PortalFile.checksum_md5,
                PortalFile.checksum_sha256,
                PortalFile.width,
                PortalFile.height,
                PortalFile.duration_seconds,
                PortalFile.status,
                PortalFile.version,
                PortalFile.is_public,
                PortalFile.source
            )
            .where(PortalFile.checksum_sha256 == checksum_sha256)
            .where(PortalFile.status != FileStatus.DELETED)
            .fetchrow(as_model=FileDetail)
        )

        return existing_file

    @distributed_trace()
    async def check_duplicate_by_multiple_checksums(
        self,
        file_content: bytes,
        content_type: str,
        file_size: int
    ) -> Optional[FileDetail]:
        """
        Check for duplicate files using multiple criteria for better accuracy

        :param file_content: File content bytes
        :param content_type: MIME type
        :param file_size: File size in bytes
        :return: Existing file if found, None otherwise
        """
        md5_hash = hashlib.md5(file_content).hexdigest()
        sha256_hash = hashlib.sha256(file_content).hexdigest()

        # First check by SHA-256 (most reliable)
        existing_file = await self.check_duplicate_file(file_content, sha256_hash)
        if existing_file:
            return existing_file

        # If SHA-256 doesn't match, check by MD5 + size + content_type
        # This helps catch files that might have been corrupted during upload
        existing_file: Optional[FileDetail] = await (
            self._session.select(
                PortalFile.id,
                PortalFile.original_name,
                PortalFile.key,
                PortalFile.storage,
                PortalFile.bucket,
                PortalFile.region,
                PortalFile.content_type,
                PortalFile.extension,
                PortalFile.size_bytes,
                PortalFile.checksum_md5,
                PortalFile.checksum_sha256,
                PortalFile.width,
                PortalFile.height,
                PortalFile.duration_seconds,
                PortalFile.status,
                PortalFile.version,
                PortalFile.is_public,
                PortalFile.source
            )
            .where(PortalFile.checksum_md5 == md5_hash)
            .where(PortalFile.size_bytes == file_size)
            .where(PortalFile.content_type == content_type)
            .where(PortalFile.status != FileStatus.DELETED)
            .fetchrow(as_model=FileDetail)
        )

        return existing_file

    @distributed_trace()
    async def get_file_info(self, file_id: uuid.UUID) -> Optional[FileDetail]:
        """
        Get file information from database
        :param file_id: PortalFile ID
        :return: PortalFile instance or None if not found
        """
        file: Optional[FileDetail] = await (
            self._session.select(
                PortalFile.id,
                PortalFile.original_name,
                PortalFile.key,
                PortalFile.storage,
                PortalFile.bucket,
                PortalFile.region,
                PortalFile.content_type,
                PortalFile.extension,
                PortalFile.size_bytes,
                PortalFile.checksum_md5,
                PortalFile.checksum_sha256,
                PortalFile.width,
                PortalFile.height,
                PortalFile.duration_seconds,
                PortalFile.status,
                PortalFile.version,
                PortalFile.is_public,
                PortalFile.source
            )
            .where(PortalFile.id == file_id)
            .where(PortalFile.status != FileStatus.DELETED)
            .fetchrow(as_model=FileDetail)
        )
        if not file:
            return None
        return file

    @distributed_trace()
    async def delete_files(self, model: BulkAction) -> BulkActionResponseModel:
        """
        Delete files from S3 and mark as deleted in database
        :param model:
        :return:
        """
        files: list[FileBase] = await (
            self._session.select(
                PortalFile.id,
                PortalFile.original_name,
                PortalFile.key,
                PortalFile.storage,
                PortalFile.bucket,
                PortalFile.region
            )
            .where(PortalFile.id.in_(model.ids))
            .fetch(as_model=FileBase)
        )

        if not files:
            raise BadRequestException("No files to delete")

        file_key_mapping = {file.key: file for file in files}
        success_keys = []
        failed_items = []
        buckets = set([file.bucket for file in files])
        for bucket in buckets:
            delete_objects = []
            for file in files:
                if file.bucket == bucket:
                    delete_objects.append({"Key": file.key})
            if delete_objects:
                try:
                    response = self._s3_client.delete_objects(
                        Bucket=bucket,
                        Delete={"Objects": delete_objects}
                    )
                    print(response)
                    deleted_items = response.get("Deleted", [])
                    for deleted in deleted_items:
                        success_keys.append(deleted['Key'])
                    error_list = response.get("Errors", [])
                    for error in error_list:
                        failed_items.append(file_key_mapping.get(error['Key'], None))
                except Exception as e:
                    failed_items.extend([file_key_mapping.get(obj["Key"], None) for obj in delete_objects])
                    logger.warning(f"Failed to delete objects in bucket {bucket}: {str(e)}")
        if success_keys:
            await (
                self._session.update(PortalFile)
                .values(status=FileStatus.DELETED)
                .where(PortalFile.key.in_(success_keys))
                .execute()
            )
        return BulkActionResponseModel(
            success_count=len(success_keys),
            failed_items=failed_items
        )
