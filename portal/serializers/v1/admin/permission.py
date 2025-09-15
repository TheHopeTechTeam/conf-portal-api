"""
Permission serializers
"""
import ujson as json
from typing import Optional
from uuid import UUID

import pydantic
from pydantic import Field, BaseModel, field_validator, field_serializer, model_serializer, model_validator

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import PaginationBaseResponseModel


class PermissionResourceItem(UUIDBaseModel):
    """PermissionResourceItem"""
    name: str = Field(..., description="Name")
    key: str = Field(..., description="Key")
    code: str = Field(..., description="Code")

    @model_validator(mode="before")
    def validate_json_string(cls, values):
        """

        :param values:
        :return:
        """
        if isinstance(values, str):
            try:
                values = json.loads(values)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string: {e}")
        return values


class PermissionVerbItem(UUIDBaseModel):
    """PermissionVerbItem"""
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    action: str = Field(..., description="Action")

    @model_validator(mode="before")
    def validate_json_string(cls, values):
        """

        :param values:
        :return:
        """
        if isinstance(values, str):
            try:
                values = json.loads(values)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string: {e}")
        return values


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
