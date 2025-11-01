"""
Permission serializers
"""
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel


class PermissionResourceItem(UUIDBaseModel, JSONStringMixinModel):
    """PermissionResourceItem"""
    name: str = Field(..., description="Name")
    key: str = Field(..., description="Key")
    code: str = Field(..., description="Code")


class PermissionVerbItem(UUIDBaseModel, JSONStringMixinModel):
    """PermissionVerbItem"""
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    action: str = Field(..., description="Action")


class PermissionBase(UUIDBaseModel):
    """PermissionBase"""
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    code: str = Field(..., description="Code")
    is_active: bool = Field(..., serialization_alias="isActive", description="Is active")
    description: Optional[str] = Field(None, description="Description")
    remark: Optional[str] = Field(None, description="Remark")


class PermissionItem(PermissionBase):
    """PermissionItem"""
    resource_id: Optional[UUID] = Field(None, serialization_alias="resourceId", description="Resource ID")
    verb_id: Optional[UUID] = Field(None, serialization_alias="verbId", description="Verb ID")


class PermissionDetail(PermissionBase):
    """PermissionDetail"""
    resource: PermissionResourceItem = Field(..., description="Resource")
    verb: PermissionVerbItem = Field(..., description="Verb")


class PermissionPageItem(PermissionBase):
    """PermissionPageItem"""
    resource_name: str = Field(..., serialization_alias="resourceName", description="Resource name")
    verb_name: str = Field(..., serialization_alias="verbName", description="Verb name")


class PermissionPage(PaginationBaseResponseModel):
    """PermissionPage"""
    items: Optional[list[PermissionPageItem]] = Field(..., description="Permissions")


class PermissionQuery(GenericQueryBaseModel):
    """PermissionQuery"""
    is_active: Optional[bool] = Field(None, description="Is active")


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


class PermissionBulkAction(BaseModel):
    """PermissionBulkAction"""
    ids: list[UUID] = Field(..., description="Permission IDs for bulk action")
