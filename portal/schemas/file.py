"""
File-related schemas for internal use (e.g. ORM fetch row shapes), not HTTP API contracts.
"""
from uuid import UUID

from pydantic import Field

from portal.schemas.mixins import UUIDBaseModel


class SignedUrlFileByResourceRow(UUIDBaseModel):
    """
    One portal_file row joined to portal_file_association.resource_id for batch signed URL queries.
    """

    resource_id: UUID = Field(..., description="Associated resource ID")
    original_name: str = Field(..., description="Original file name")
    key: str = Field(..., description="Storage object key")
    storage: str = Field(..., description="Storage backend")
    bucket: str = Field(..., description="Bucket name")
    region: str = Field(..., description="Region")
