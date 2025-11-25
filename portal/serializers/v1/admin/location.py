"""
Location serializers
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel
from portal.serializers.v1.admin.file import AdminFileGridItem


class AdminLocationQuery(GenericQueryBaseModel):
    """
    Location query model
    """
    room_number: Optional[str] = Field(None, description="Room number")


class AdminLocationBase(UUIDBaseModel, JSONStringMixinModel):
    """
    Location base model
    """
    name: str = Field(..., description="Name")


class AdminLocationItem(AdminLocationBase):
    """
    Location item
    """
    address: Optional[str] = Field(None, description="Address")
    floor: Optional[str] = Field(None, description="Floor")
    room_number: Optional[str] = Field(None, serialization_alias="roomNumber", description="Room number")
    remark: Optional[str] = Field(None, description="Remark")
    created_at: Optional[datetime] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updatedAt", description="Updated at")


class AdminLocationDetail(AdminLocationItem):
    """Location detail"""
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    description: Optional[str] = Field(None, description="Description")
    files: Optional[list[AdminFileGridItem]] = Field(None, description="Files")


class AdminLocationPages(PaginationBaseResponseModel):
    """Location pages"""
    items: Optional[list[AdminLocationItem]] = Field(..., description="Items")


class AdminLocationList(BaseModel):
    """Location list"""
    items: Optional[list[AdminLocationBase]] = Field(..., description="Items")


class AdminLocationCreate(BaseModel):
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


class AdminLocationUpdate(AdminLocationCreate):
    """Location update"""
