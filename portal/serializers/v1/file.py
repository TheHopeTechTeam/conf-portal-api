"""
File Serializer
"""
from typing import Optional

from pydantic import BaseModel, Field

from portal.libs.consts.enums import FileStatus, FileUploadSource
from portal.schemas.mixins import UUIDBaseModel


class FailedUploadFile(BaseModel):
    """Fail Upload File"""
    filename: str = Field(..., description="File name")
    error: str = Field(..., description="Error message")

class BatchFileUploadResponseModel(BaseModel):
    """Batch File Upload Response Model"""
    uploaded_files: list[UUIDBaseModel] = Field(..., description="Uploaded files")
    failed_files: list[FailedUploadFile] = Field(..., description="Failed files")

class FileBase(UUIDBaseModel):
    """File Base Model"""
    original_name: str = Field(..., description="Original file name")
    key: str = Field(..., description="Key")
    storage: str = Field(..., description="Storage")
    bucket: str = Field(..., description="Bucket")
    region: str = Field(..., description="Region")
    content_type: Optional[str] = Field(None, description="Content type")
    extension: Optional[str] = Field(None, description="File extension")
    size_bytes: Optional[int] = Field(None, description="Size in bytes")
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum")
    checksum_sha256: Optional[str] = Field(None, description="SHA256 checksum")
    width: Optional[int] = Field(None, description="Width")
    height: Optional[int] = Field(None, description="Height")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds")
    status: Optional[FileStatus] = Field(None, description="File status")
    version: Optional[int] = Field(None, description="File version")
    is_public: Optional[bool] = Field(None, description="Is public")
    source: Optional[FileUploadSource] = Field(None, description="Source")


class FileUploadResponseModel(UUIDBaseModel):
    """File Upload Response Model"""
    duplicate: Optional[bool] = Field(None, description="Is duplicate")
