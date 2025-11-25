"""
Workshop Registration serializers
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel
from portal.serializers.v1.admin.user import AdminUserBase
from portal.serializers.v1.admin.workshop import AdminWorkshopBase


class AdminWorkshopRegistrationQuery(GenericQueryBaseModel):
    """
    Workshop Registration query model
    """
    workshop_id: Optional[UUID] = Field(default=None, description="Workshop ID")
    is_registered: Optional[bool] = Field(default=True, description="Is registered (unregistered_at is None)")


class AdminWorkshopRegistrationItem(UUIDBaseModel):
    """Workshop Registration page item"""
    workshop_title: Optional[str] = Field(default=None, serialization_alias="workshopTitle", description="Workshop title")
    user_email: Optional[str] = Field(default=None, serialization_alias="userEmail", description="User email")
    user_display_name: Optional[str] = Field(default=None, serialization_alias="userDisplayName", description="User display name")
    registered_at: datetime = Field(..., serialization_alias="registeredAt", description="Registration time")
    unregistered_at: Optional[datetime] = Field(default=None, serialization_alias="unregisteredAt", description="Unregistration time")


class AdminWorkshopRegistrationDetail(UUIDBaseModel):
    """Workshop Registration detail"""
    workshop: AdminWorkshopBase = Field(..., description="Workshop")
    user: AdminUserBase = Field(..., description="User")


class AdminWorkshopRegistrationPages(PaginationBaseResponseModel):
    """Workshop Registration pages"""
    items: Optional[list[AdminWorkshopRegistrationItem]] = Field(..., description="Items")


class AdminWorkshopRegistrationCreate(BaseModel):
    """Workshop Registration create"""
    workshop_id: UUID = Field(..., description="Workshop ID")
    user_id: UUID = Field(..., description="User ID")
