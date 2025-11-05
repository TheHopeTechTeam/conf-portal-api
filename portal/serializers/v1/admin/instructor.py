"""
Instructor serializers
"""

from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel


class InstructorQuery(GenericQueryBaseModel):
    """
    Instructor query model
    """
    pass


class InstructorBase(UUIDBaseModel):
    """
    Instructor base model
    """
    name: str = Field(..., description="Name")
    title: Optional[str] = Field(None, description="Title")
    bio: Optional[str] = Field(None, description="Bio")
    remark: Optional[str] = Field(None, description="Remark")
    created_at: Optional[str] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[str] = Field(None, serialization_alias="updatedAt", description="Updated at")


class InstructorItem(InstructorBase):
    """
    Instructor item
    """
    description: Optional[str] = Field(None, description="Description")


class InstructorDetail(InstructorItem):
    """Instructor detail"""
    image_urls: Optional[list[str]] = Field(None, serialization_alias="imageUrl", description="Image URLs")


class InstructorPages(PaginationBaseResponseModel):
    """Instructor pages"""
    items: Optional[list[InstructorItem]] = Field(..., description="Items")


class InstructorCreate(BaseModel):
    """Instructor create"""
    name: str = Field(..., description="Name")
    title: Optional[str] = Field(None, description="Title")
    bio: Optional[str] = Field(None, description="Bio")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")
    file_ids: Optional[list[UUID]] = Field(None, serialization_alias="fileIds", description="File IDs")


class InstructorUpdate(InstructorCreate):
    """Instructor update"""

