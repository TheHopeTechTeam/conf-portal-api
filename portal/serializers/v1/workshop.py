"""
Workshop serializers
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel
from portal.serializers.v1.instructor import InstructorBase
from portal.serializers.v1.location import LocationBase


class WorkshopBase(UUIDBaseModel, JSONStringMixinModel):
    """
    Workshop
    """
    title: str = Field(..., description="Title")
    description: str = Field(..., description="Description")
    location: LocationBase = Field(..., description="Location")
    slido_url: Optional[str] = Field(default=None, serialization_alias="slidoUrl", description="Slido URL")
    is_full: bool = Field(..., serialization_alias="isFull", description="The number of participants has reached the upper limit")
    # exclude fields for response
    start_datetime: Optional[datetime] = Field(None, description="Start Date and Time", exclude=True)
    end_datetime: Optional[datetime] = Field(None, description="End Date and Time", exclude=True)
    participants_limit: Optional[int] = Field(default=None, description="Participants Limit", exclude=True)
    timezone: Optional[str] = Field(default=None, description="Time Zone", exclude=True)


class WorkshopDetail(WorkshopBase):
    """
    Workshop detail
    """
    # conference: str = Field(..., description="Conference")
    start_datetime: datetime = Field(..., serialization_alias="startDatetime", description="Start Date and Time")
    end_datetime: datetime = Field(..., serialization_alias="endDatetime", description="End Date and Time")
    instructor: InstructorBase = Field(..., description="Instructor")
    participants_limit: int = Field(..., serialization_alias="participantsLimit", description="Participants Limit")
    image_url: Optional[str] = Field(default=None, serialization_alias="imageUrl", description="Image URL")


class WorkshopRegistered(WorkshopBase):
    """
    Workshop registered
    """
    start_datetime: datetime = Field(..., serialization_alias="startDatetime", description="Start Date and Time")
    end_datetime: datetime = Field(..., serialization_alias="endDatetime", description="End Date and Time")
    is_registered: bool = Field(default=True, serialization_alias="isRegistered", description="Is registered")


class WorkshopRegisteredList(BaseModel):
    """
    Workshop registered list
    """
    workshops: list[WorkshopRegistered] = Field(..., description="Workshops")


class WorkshopSchedule(BaseModel):
    """
    Workshop schedule
    """
    start_datetime: datetime = Field(..., serialization_alias="startDatetime", description="Start Date and Time")
    end_datetime: datetime = Field(..., serialization_alias="endDatetime", description="End Date and Time")
    workshops: list[WorkshopBase] = Field(..., description="Workshops")


class WorkshopScheduleList(BaseModel):
    """
    Workshop schedule
    """
    schedule: list[WorkshopSchedule] = Field(..., description="Schedule")
