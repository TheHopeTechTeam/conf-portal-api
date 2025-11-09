"""
Event info serializers
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.admin.conference import ConferenceBase


class EventInfoQuery(BaseModel):
    """Event info query model"""
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")


class EventInfoBase(UUIDBaseModel):
    """Event info base model"""
    title: str = Field(..., description="Title")


class EventInfoItem(EventInfoBase):
    """Event info item"""
    start_datetime: datetime = Field(..., serialization_alias="startTime", description="Start Datetime")
    end_datetime: datetime = Field(..., serialization_alias="endTime", description="End Datetime")
    timezone: str = Field(..., description="Timezone")
    text_color: str = Field(..., serialization_alias="textColor", description="Text color")
    background_color: str = Field(..., serialization_alias="backgroundColor", description="Background color")


class EventInfoDetail(EventInfoItem):
    """Event info detail"""
    remark: Optional[str] = Field(default=None, description="Remark")
    description: Optional[str] = Field(default=None, description="Description")
    conference: ConferenceBase = Field(..., description="Conference")


class EventInfoList(BaseModel):
    """Event info list"""
    items: Optional[list[EventInfoItem]] = Field(..., description="Items")


class EventInfoCreate(BaseModel):
    """Event info create"""
    title: str = Field(..., description="Title")
    start_datetime: datetime = Field(..., serialization_alias="startTime", description="Start Datetime")
    end_datetime: datetime = Field(..., serialization_alias="endTime", description="End Datetime")
    timezone: str = Field(..., description="Timezone")
    text_color: Optional[str] = Field(..., serialization_alias="textColor", description="Text color")
    background_color: Optional[str] = Field(..., serialization_alias="backgroundColor", description="Background color")
    conference_id: UUID = Field(..., serialization_alias="conferenceId", description="Conference ID")
    remark: Optional[str] = Field(default=None, description="Remark")
    description: Optional[str] = Field(default=None, description="Description")


class EventInfoUpdate(EventInfoCreate):
    """Event info update"""
