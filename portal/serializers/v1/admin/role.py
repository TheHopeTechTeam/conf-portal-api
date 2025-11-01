"""
Role serializers
"""
from datetime import datetime

import ujson
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel, model_validator

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import PaginationBaseResponseModel


class RolePermission(UUIDBaseModel):
    """PermissionBase"""
    resource_name: str = Field(..., serialization_alias="resourceName", description="Resource name")
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    code: str = Field(..., description="Code")

    @model_validator(mode="before")
    def validate_json_string(cls, values):
        """

        :param values:
        :return:
        """
        if isinstance(values, str):
            try:
                values = ujson.loads(values)
            except ujson.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string: {e}")
        return values


class RoleItem(UUIDBaseModel):
    """RoleItem"""
    code: str = Field(..., description="Role code")
    name: Optional[str] = Field(None, description="Role name")
    is_active: bool = Field(True, serialization_alias="isActive", description="Is role active")


class RoleTableItem(RoleItem):
    """RoleTableItem"""
    created_at: Optional[datetime] = Field(None, serialization_alias="createAt", description="Create at")
    created_by: Optional[str] = Field(None, serialization_alias="createdBy", description="Created by")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updateAt", description="Update at")
    updated_by: Optional[str] = Field(None, serialization_alias="updatedBy", description="Updated by")
    delete_reason: Optional[str] = Field(None, serialization_alias="deleteReason", description="Delete reason")
    description: Optional[str] = Field(None, description="Description")
    remark: Optional[str] = Field(None, description="Remark")
    permissions: list[RolePermission] = Field(..., description="Permissions")


class RolePages(PaginationBaseResponseModel):
    """RolePages"""
    items: Optional[list[RoleTableItem]] = Field(..., description="Role Items")


class RoleList(BaseModel):
    """RoleList"""
    items: Optional[list[RoleItem]] = Field(..., description="Role Items")


class RoleCreate(BaseModel):
    """RoleCreate"""
    code: str = Field(..., description="Role code")
    name: Optional[str] = Field(None, description="Role name")
    is_active: bool = Field(True, serialization_alias="isActive", description="Is role active")
    description: Optional[str] = Field(None, description="Description")
    remark: Optional[str] = Field(None, description="Remark")
    permissions: list[UUID] = Field(..., description="Permissions")


class RoleUpdate(RoleCreate):
    """RoleUpdate"""
    pass


class RoleBulkDelete(BaseModel):
    """RoleBulkDelete"""
    ids: list[UUID] = Field(..., description="Role IDs to delete")


class RolePermissionAssign(BaseModel):
    """Assign or revoke permissions to a role"""
    permission_ids: list[UUID] = Field(..., serialization_alias="permissionIds", description="Permission IDs to assign or revoke")
