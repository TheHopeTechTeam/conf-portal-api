"""
Permission serializers
"""
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel


class PermissionResourceItem(UUIDBaseModel, JSONStringMixinModel):
    """PermissionResourceItem"""
    name: str = Field(..., description="Name")
    key: str = Field(..., description="Key")
    code: str = Field(..., description="Code")


class PermissionVerbItem(UUIDBaseModel, JSONStringMixinModel):
    """PermissionVerbItem"""
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    action: str = Field(..., description="Action")


class PermissionItem(UUIDBaseModel):
    """PermissionItem"""
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    code: str = Field(..., description="Code")
    resource: PermissionResourceItem = Field(..., description="Resource")
    verb: PermissionVerbItem = Field(..., description="Verb")
    is_active: bool = Field(..., serialization_alias="isActive", description="Is active")
    description: Optional[str] = Field(None, description="Description")
    remark: Optional[str] = Field(None, description="Remark")


class PermissionCreate(BaseModel):
    """PermissionCreate"""
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    code: str = Field(..., description="Code")
    resource_id: UUID = Field(..., serialization_alias="resourceId", description="Resource ID")
    verb_id: UUID = Field(..., serialization_alias="verbId", description="Verb ID")
    is_active: bool = Field(..., serialization_alias="isActive", description="Is active")
    description: Optional[str] = Field(None, description="Description")
    remark: Optional[str] = Field(None, description="Remark")


class PermissionUpdate(PermissionCreate):
    """PermissionUpdate"""


class PermissionList(BaseModel):
    """PermissionList"""
    items: Optional[list[PermissionItem]] = Field(..., description="Permissions")
