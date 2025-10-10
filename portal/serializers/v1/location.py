"""
Location serializers
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel


class LocationBase(UUIDBaseModel, JSONStringMixinModel):
    name: str = Field(..., description="Location name")
    address: Optional[str] = Field(None, description="Location address")
    floor: Optional[str] = Field(None, description="Location floor")
    room_number: Optional[str] = Field(None, serialization_alias="roomNumber", description="Location room number")
    image_url: Optional[str] = Field(None, serialization_alias="imageUrl", description="Image URL")
