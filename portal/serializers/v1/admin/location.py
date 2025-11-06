"""
Location serializers
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel
from portal.serializers.v1.admin.file import FileGridItem


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


class LocationItem(LocationBase):
    """
    Location item
    """
    address: Optional[str] = Field(None, description="Address")
    floor: Optional[str] = Field(None, description="Floor")
    room_number: Optional[str] = Field(None, serialization_alias="roomNumber", description="Room number")
    remark: Optional[str] = Field(None, description="Remark")
    created_at: Optional[datetime] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updatedAt", description="Updated at")


class LocationDetail(LocationItem):
    """Location detail"""
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    description: Optional[str] = Field(None, description="Description")
    files: Optional[list[FileGridItem]] = Field(None, description="Files")


class LocationPages(PaginationBaseResponseModel):
    """Location pages"""
    items: Optional[list[LocationItem]] = Field(..., description="Items")


class LocationCreate(BaseModel):
    """Location create"""
    name: str = Field(..., description="Name")
    address: Optional[str] = Field(None, description="Address")
    floor: Optional[str] = Field(None, description="Floor")
    room_number: Optional[str] = Field(None, description="Room number")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")
    file_ids: Optional[list[UUID]] = Field(None, description="File IDs")


class LocationUpdate(LocationCreate):
    """Location update"""
