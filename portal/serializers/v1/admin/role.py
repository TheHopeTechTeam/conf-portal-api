"""
Role serializers
"""
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import PaginationBaseResponseModel


class RoleItem(UUIDBaseModel):
    """RoleItem"""
    code: str = Field(..., description="Role code")
    name: Optional[str] = Field(None, description="Role name")
    is_active: bool = Field(True, serialization_alias="isActive", description="Is role active")


class RolePages(PaginationBaseResponseModel):
    """RolePages"""
    items: Optional[list[RoleItem]] = Field(..., description="Role Items")


class RoleList(BaseModel):
    """RoleList"""
    items: Optional[list[RoleItem]] = Field(..., description="Role Items")


class RoleCreate(BaseModel):
    """RoleCreate"""
    code: str = Field(..., description="Role code")
    name: Optional[str] = Field(None, description="Role name")
    is_active: bool = Field(True, serialization_alias="isActive", description="Is role active")


class RoleUpdate(RoleCreate):
    """RoleUpdate"""
    pass


class RoleBulkDelete(BaseModel):
    """RoleBulkDelete"""
    ids: list[UUID] = Field(..., description="Role IDs to delete")


class RolePermissionAssign(BaseModel):
    """Assign or revoke permissions to a role"""
    permission_ids: list[UUID] = Field(..., serialization_alias="permissionIds", description="Permission IDs")


