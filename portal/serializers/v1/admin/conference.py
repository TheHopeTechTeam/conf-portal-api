"""
Conference serializers
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel
from portal.serializers.v1.admin.location import LocationBase


class ConferenceQuery(GenericQueryBaseModel):
    """
    Conference query model
    """
    is_active: Optional[bool] = Field(default=None, description="Is Active")


class ConferenceBase(UUIDBaseModel, JSONStringMixinModel):
    """
    Conference base model
    """
    title: str = Field(..., description="Title")


class ConferenceItem(ConferenceBase):
    """
    Conference item
    """
    start_date: date = Field(..., serialization_alias="startDate", description="Start Date")
    end_date: date = Field(..., serialization_alias="endDate", description="End Date")
    is_active: Optional[bool] = Field(default=None, serialization_alias="isActive", description="Is Active")
    remark: Optional[str] = Field(default=None, description="Remark")
    created_at: Optional[datetime] = Field(default=None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[datetime] = Field(default=None, serialization_alias="updatedAt", description="Updated at")
    description: Optional[str] = Field(default=None, description="Description")
    location_name: Optional[str] = Field(default=None, serialization_alias="locationName", description="Location name")


class ConferenceDetail(ConferenceBase):
    """
    Conference detail
    """
    start_date: date = Field(..., serialization_alias="startDate", description="Start Date")
    end_date: date = Field(..., serialization_alias="endDate", description="End Date")
    is_active: Optional[bool] = Field(default=None, serialization_alias="isActive", description="Is Active")
    remark: Optional[str] = Field(default=None, description="Remark")
    created_at: Optional[datetime] = Field(default=None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[datetime] = Field(default=None, serialization_alias="updatedAt", description="Updated at")
    description: Optional[str] = Field(default=None, description="Description")
    location: Optional[LocationBase] = Field(default=None, description="Location object with id and name")


class ConferencePages(PaginationBaseResponseModel):
    """Conference pages"""
    items: Optional[list[ConferenceItem]] = Field(..., description="Items")


class ConferenceList(BaseModel):
    """Conference list"""
    items: Optional[list[ConferenceBase]] = Field(..., description="Items")


class ConferenceCreate(BaseModel):
    """Conference create"""
    title: str = Field(..., description="Title")
    timezone: str = Field(..., description="Timezone")
    start_date: date = Field(..., serialization_alias="startDate", description="Start Date")
    end_date: date = Field(..., serialization_alias="endDate", description="End Date")
    is_active: Optional[bool] = Field(default=True, serialization_alias="isActive", description="Is Active")
    location_id: Optional[UUID] = Field(default=None, serialization_alias="locationId", description="Location ID")
    remark: Optional[str] = Field(default=None, description="Remark")
    description: Optional[str] = Field(default=None, description="Description")


class ConferenceUpdate(ConferenceCreate):
    """Conference update"""


class ConferenceInstructorItem(BaseModel):
    """Conference instructor mapping item"""
    instructor_id: UUID = Field(..., description="Instructor ID")
    is_primary: bool = Field(default=False, description="Is primary instructor")
    sequence: int = Field(..., description="Display order (small to large)")


class ConferenceInstructorsUpdate(BaseModel):
    """Update conference instructors"""
    instructors: list[ConferenceInstructorItem] = Field(..., description="Instructor mapping list")
