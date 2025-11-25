"""
Permission serializers
"""
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel


class AdminPermissionResourceItem(UUIDBaseModel, JSONStringMixinModel):
    """PermissionResourceItem"""
    name: str = Field(..., description="Name")
    key: str = Field(..., description="Key")
    code: str = Field(..., description="Code")


class AdminPermissionVerbItem(UUIDBaseModel, JSONStringMixinModel):
    """PermissionVerbItem"""
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    action: str = Field(..., description="Action")


class AdminPermissionBase(UUIDBaseModel):
    """PermissionBase"""
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    code: str = Field(..., description="Code")
    is_active: bool = Field(..., serialization_alias="isActive", description="Is active")
    description: Optional[str] = Field(None, description="Description")
    remark: Optional[str] = Field(None, description="Remark")


class AdminPermissionItem(AdminPermissionBase):
    """PermissionItem"""
    resource_id: Optional[UUID] = Field(None, serialization_alias="resourceId", description="Resource ID")
    verb_id: Optional[UUID] = Field(None, serialization_alias="verbId", description="Verb ID")


class AdminPermissionDetail(AdminPermissionBase):
    """PermissionDetail"""
    resource: AdminPermissionResourceItem = Field(..., description="Resource")
    verb: AdminPermissionVerbItem = Field(..., description="Verb")


class AdminPermissionPageItem(AdminPermissionBase):
    """PermissionPageItem"""
    resource_name: str = Field(..., serialization_alias="resourceName", description="Resource name")
    verb_name: str = Field(..., serialization_alias="verbName", description="Verb name")


class AdminPermissionPage(PaginationBaseResponseModel):
    """PermissionPage"""
    items: Optional[list[AdminPermissionPageItem]] = Field(..., description="Permissions")


class AdminPermissionQuery(GenericQueryBaseModel):
    """PermissionQuery"""
    is_active: Optional[bool] = Field(None, description="Is active")


class AdminPermissionCreate(BaseModel):
    """PermissionCreate"""
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    code: str = Field(..., description="Code")
    resource_id: UUID = Field(..., serialization_alias="resourceId", description="Resource ID")
    verb_id: UUID = Field(..., serialization_alias="verbId", description="Verb ID")
    is_active: bool = Field(..., serialization_alias="isActive", description="Is active")
    description: Optional[str] = Field(None, description="Description")
    remark: Optional[str] = Field(None, description="Remark")


class AdminPermissionUpdate(AdminPermissionCreate):
    """PermissionUpdate"""


class AdminPermissionList(BaseModel):
    """PermissionList"""
    items: Optional[list[AdminPermissionItem]] = Field(..., description="Permissions")


class AdminPermissionBulkAction(BaseModel):
    """PermissionBulkAction"""
    ids: list[UUID] = Field(..., description="Permission IDs for bulk action")
