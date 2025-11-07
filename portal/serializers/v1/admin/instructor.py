"""
Instructor serializers
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel
from portal.serializers.v1.admin.file import FileGridItem


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
    created_at: Optional[datetime] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updatedAt", description="Updated at")


class InstructorItem(InstructorBase):
    """
    Instructor item
    """
    description: Optional[str] = Field(None, description="Description")


class InstructorDetail(InstructorItem):
    """Instructor detail"""
    files: Optional[list[FileGridItem]] = Field(None, description="Files")


class InstructorPages(PaginationBaseResponseModel):
    """Instructor pages"""
    items: Optional[list[InstructorBase]] = Field(..., description="Items")


class InstructorCreate(BaseModel):
    """Instructor create"""
    name: str = Field(..., description="Name")
    title: Optional[str] = Field(None, description="Title")
    bio: Optional[str] = Field(None, description="Bio")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")
    file_ids: Optional[list[UUID]] = Field(None, description="File IDs")


class InstructorUpdate(InstructorCreate):
    """Instructor update"""

