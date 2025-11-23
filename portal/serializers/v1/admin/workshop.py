"""
Workshop serializers
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel
from portal.serializers.mixins.base import ChangeSequence
from portal.serializers.v1.admin.location import LocationBase
from portal.serializers.v1.admin.conference import ConferenceBase


class WorkshopQuery(GenericQueryBaseModel):
    """
    Workshop query model
    """
    is_active: Optional[bool] = Field(default=True, description="Active Conference's Workshop")
    location_id: Optional[UUID] = Field(default=None, description="Location ID")
    conference_id: Optional[UUID] = Field(default=None, description="Conference ID")
    start_datatime: Optional[datetime] = Field(default=None, description="Start Datetime")
    end_datatime: Optional[datetime] = Field(default=None, description="End Datetime")


class WorkshopBase(UUIDBaseModel, JSONStringMixinModel):
    """Workshop base model"""
    title: str = Field(..., description="Title")


class WorkshopItem(WorkshopBase):
    """Workshop item"""
    timezone: str = Field(..., description="Timezone")
    start_datetime: datetime = Field(..., serialization_alias="startTime", description="Start Datetime")
    end_datetime: datetime = Field(..., serialization_alias="endTime", description="End Datetime")
    participant_limit: Optional[int] = Field(None, serialization_alias="participantLimit", description="Participants Limit")
    remark: Optional[str] = Field(None, description="Remark")
    sequence: float = Field(..., description="Display order (small to large)")


class WorkshopSequenceItem(UUIDBaseModel):
    """Workshop sequence item"""
    sequence: float = Field(..., description="Display order (small to large)")


class WorkshopDetail(WorkshopItem):
    """Workshop detail"""
    location: LocationBase = Field(..., description="Location")
    conference: ConferenceBase = Field(..., description="Conference")
    description: Optional[str] = Field(None, description="Description")


class WorkshopPageItem(WorkshopItem):
    """Workshop page item"""
    conference_title: Optional[str] = Field(default=None, serialization_alias="conferenceTitle", description="Conference title")
    location_name: Optional[str] = Field(default=None, serialization_alias="locationName", description="Location name")
    registered_count: int = Field(..., serialization_alias="registeredCount", description="Registered count")


class WorkshopPages(PaginationBaseResponseModel):
    """Workshop pages"""
    items: Optional[list[WorkshopPageItem]] = Field(..., description="Items")
    prev_item: Optional[WorkshopSequenceItem] = Field(None, serialization_alias="prevItem", description="Previous workshop item")
    next_item: Optional[WorkshopSequenceItem] = Field(None, serialization_alias="nextItem", description="Next workshop item")


class WorkshopCreate(BaseModel):
    """Workshop create"""
    title: str = Field(..., description="Title")
    timezone: str = Field(..., description="Timezone")
    start_datetime: datetime = Field(..., description="Start Datetime")
    end_datetime: datetime = Field(..., description="End Datetime")
    location_id: UUID = Field(..., description="Location ID")
    conference_id: UUID = Field(..., description="Conference ID")
    participant_limit: Optional[int] = Field(None, description="Participants Limit")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")


class WorkshopUpdate(WorkshopCreate):
    """Workshop update"""


class WorkshopChangeSequence(ChangeSequence):
    """Workshop change sequence"""


class WorkshopInstructorBase(BaseModel):
    """Workshop instructor mapping item"""
    instructor_id: UUID = Field(..., description="Instructor ID")
    is_primary: bool = Field(default=False, description="Is primary instructor")
    sequence: int = Field(..., description="Display order (small to large)")


class WorkshopInstructorItem(WorkshopInstructorBase):
    """Workshop instructor mapping item"""
    name: str = Field(..., description="Instructor name")
    sequence: float = Field(..., description="Display order (small to large)")


class WorkshopInstructors(BaseModel):
    """Workshop instructors"""
    items: list[WorkshopInstructorItem] = Field(..., description="Instructor mapping list")


class WorkshopInstructorsUpdate(BaseModel):
    """Update workshop instructors"""
    instructors: list[WorkshopInstructorBase] = Field(..., description="Instructor mapping list")
