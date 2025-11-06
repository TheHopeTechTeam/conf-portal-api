"""
Event Info Serializer
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel


class EventScheduleBase(UUIDBaseModel):
    """
    Event Schedule Base
    """
    title: str = Field(..., description="Title")
    description: Optional[str] = Field(None, description="Description")
    start_time: datetime = Field(..., serialization_alias="startTime", description="Start Time")
    time_zone: Optional[str] = Field(None, serialization_alias="timeZone", description="Time Zone", exclude=True)
    background_color: Optional[str] = Field(None, serialization_alias="backgroundColor", description="Color")


class EventScheduleItem(BaseModel):
    """
    Event Schedule Item
    """
    date: datetime = Field(..., title="Date")
    weekday: str = Field(..., title="Week Day")
    schedules: list[EventScheduleBase] = Field(..., title="Schedules")

class EventScheduleList(BaseModel):
    """
    Event Schedule List
    """
    schedules: list[EventScheduleItem] = Field(..., title="Schedules")
