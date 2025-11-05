"""
Location serializers
"""

from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel


class LocationQuery(GenericQueryBaseModel):
    """
    Location query model
    """
    room_number: Optional[str] = Field(None, description="Room number")


class LocationBase(UUIDBaseModel):
    """
    Location base model
    """
    name: str = Field(..., description="Name")
    address: Optional[str] = Field(None, description="Address")
    floor: Optional[str] = Field(None, description="Floor")
    room_number: Optional[str] = Field(None, serialization_alias="roomNumber", description="Room number")
    remark: Optional[str] = Field(None, description="Remark")
    created_at: Optional[str] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[str] = Field(None, serialization_alias="updatedAt", description="Updated at")


class LocationItem(LocationBase):
    """
    Location item
    """
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    description: Optional[str] = Field(None, description="Description")


class LocationDetail(LocationItem):
    """Location detail"""
    image_urls: Optional[list[str]] = Field(None, serialization_alias="imageUrl", description="Image URLs")


class LocationPages(PaginationBaseResponseModel):
    """Location pages"""
    items: Optional[list[LocationItem]] = Field(..., description="Items")


class LocationCreate(BaseModel):
    """Location create"""
    name: str = Field(..., description="Name")
    address: Optional[str] = Field(None, description="Address")
    floor: Optional[str] = Field(None, description="Floor")
    room_number: Optional[str] = Field(None, serialization_alias="roomNumber", description="Room number")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")
    file_ids: Optional[list[UUID]] = Field(None, serialization_alias="fileIds", description="File IDs")


class LocationUpdate(LocationCreate):
    """Location update"""



