"""
Instructor serializers
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel
from portal.serializers.v1.admin.file import AdminFileGridItem


class AdminInstructorQuery(GenericQueryBaseModel):
    """
    Instructor query model
    """
    pass


class AdminInstructorBase(UUIDBaseModel):
    """
    Instructor base model
    """
    name: str = Field(..., description="Name")
    title: Optional[str] = Field(None, description="Title")
    bio: Optional[str] = Field(None, description="Bio")
    remark: Optional[str] = Field(None, description="Remark")
    created_at: Optional[datetime] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updatedAt", description="Updated at")


class AdminInstructorItem(AdminInstructorBase):
    """
    Instructor item
    """
    description: Optional[str] = Field(None, description="Description")


class AdminInstructorDetail(AdminInstructorItem):
    """Instructor detail"""
    files: Optional[list[AdminFileGridItem]] = Field(None, description="Files")


class AdminInstructorPages(PaginationBaseResponseModel):
    """Instructor pages"""
    items: Optional[list[AdminInstructorBase]] = Field(..., description="Items")


class AdminInstructorList(BaseModel):
    """Instructor list"""
    items: Optional[list[AdminInstructorBase]] = Field(..., description="Items")


class AdminInstructorCreate(BaseModel):
    """Instructor create"""
    name: str = Field(..., description="Name")
    title: Optional[str] = Field(None, description="Title")
    bio: Optional[str] = Field(None, description="Bio")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")
    file_ids: Optional[list[UUID]] = Field(None, description="File IDs")


class AdminInstructorUpdate(AdminInstructorCreate):
    """Instructor update"""

