"""
Model of the file table
"""
import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from portal.libs.consts.enums import FileStatus
from portal.libs.database.orm import ModelBase
from .mixins import SortableMixin, AuditMixin, RemarkMixin


class PortalFile(ModelBase, AuditMixin, RemarkMixin):
    """Portal File Model for storing uploaded file metadata"""
    __extra_table_args__ = (
        sa.UniqueConstraint("bucket", "key"),
    )
    original_name = Column(sa.String(255), nullable=False, comment="Original filename as uploaded")
    key = Column(sa.String(512), nullable=False, index=True, comment="Storage object key(path)")
    storage = Column(sa.String(16), nullable=False, default="s3", comment="Storage backend, e.g., s3, gcs, local")
    bucket = Column(sa.String(128), nullable=False, comment="S3 bucket name")
    region = Column(sa.String(32), nullable=False, comment="S3 region")
    content_type = Column(sa.String(128), nullable=True, comment="MIME type")
    extension = Column(sa.String(16), nullable=True, comment="File extension")
    size_bytes = Column(sa.BigInteger, nullable=True, comment="File size in bytes")
    checksum_md5 = Column(sa.String(32), nullable=True, comment="MD5 checksum of the file")
    checksum_sha256 = Column(sa.String(64), nullable=True, comment="SHA-256 checksum of the file")
    width = Column(sa.Integer, nullable=True, comment="Image width in pixels")
    height = Column(sa.Integer, nullable=True, comment="Image height in pixels")
    duration_seconds = Column(sa.Float, nullable=True, comment="Media duration in seconds")
    status = Column(sa.Integer, nullable=False, default=FileStatus.UPLOADING, comment="File status, refer to FileStatus enum")
    version = Column(sa.Integer, nullable=False, default=1, comment="File version number")
    is_public = Column(sa.Boolean, server_default=sa.text("false"), nullable=False, comment="Whether the file is public")
    source = Column(sa.Integer, nullable=True, comment="Upload source, refer to UploadSource enum")


class PortalFileRendition(ModelBase, AuditMixin):
    """Portal File Rendition Model for storing different image sizes"""
    __extra_table_args__ = (
        sa.UniqueConstraint("original_file_id", "rendition_type"),
    )
    original_file_id = Column(
        UUID,
        ForeignKey(PortalFile.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Original file ID"
    )
    rendition_type = Column(sa.String(32), nullable=False, comment="Rendition type, e.g., max-100x100, original")
    key = Column(sa.String(512), nullable=False, index=True, comment="Storage object key(path) for this rendition")
    storage = Column(sa.String(16), nullable=False, default="s3", comment="Storage backend for this rendition")
    bucket = Column(sa.String(128), nullable=False, comment="S3 bucket for this rendition")
    region = Column(sa.String(32), nullable=False, comment="S3 region for this rendition")
    width = Column(sa.Integer, nullable=True, comment="Rendition width in pixels")
    height = Column(sa.Integer, nullable=True, comment="Rendition height in pixels")
    size_bytes = Column(sa.BigInteger, nullable=True, comment="Rendition file size in bytes")
    checksum_md5 = Column(sa.String(32), nullable=True, comment="MD5 checksum of the rendition")


class PortalFileAssociation(ModelBase, SortableMixin):
    """Portal File Association Model for linking files to various resources"""
    file_id = Column(
        UUID,
        ForeignKey(PortalFile.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="File ID"
    )
    resource_id = Column(UUID, nullable=False, index=True, comment="Resource ID")
    resource_name = Column(sa.String(32), nullable=False, index=True, comment="Resource name(default table name)")
