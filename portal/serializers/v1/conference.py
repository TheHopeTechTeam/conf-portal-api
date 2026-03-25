"""
Conference serializers
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.instructor import InstructorBase
from portal.serializers.v1.location import LocationBase


class ConferenceBase(UUIDBaseModel):
    """
    Conference Base
    """
    title: str = Field(..., description="Title")
    start_date: date = Field(..., serialization_alias="startDate", description="Start Date")
    end_date: date = Field(..., serialization_alias="endDate", description="End Date")


class ConferenceDetail(ConferenceBase):
    """
    Conference Detail
    """
    description: str = Field(..., description="Description")
    location: Optional[LocationBase] = Field(..., description="Location")
    instructors: list[InstructorBase] = Field(..., description="Instructors")


class ConferenceList(BaseModel):
    """
    Conference List
    """
    conferences: list[ConferenceBase] = Field(..., description="Conferences")
