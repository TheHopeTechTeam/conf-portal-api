"""
FAQ serializers
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel


class AdminFaqCategoryBase(UUIDBaseModel):
    """
    FAQ Category base model
    """
    name: str = Field(..., description="Name")
    remark: Optional[str] = Field(None, description="Remark")
    sequences: Optional[float] = Field(None, description="Sequences")
    created_at: Optional[datetime] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updatedAt", description="Updated at")


class AdminFaqCategoryItem(AdminFaqCategoryBase):
    """
    FAQ Category item
    """
    description: Optional[str] = Field(None, description="Description")


class AdminFaqCategoryDetail(AdminFaqCategoryItem):
    """FAQ Category detail"""
    pass


class AdminFaqCategoryList(BaseModel):
    """FAQ Category list"""
    categories: list[AdminFaqCategoryBase] = Field(..., description="Categories")


class AdminFaqCategoryCreate(BaseModel):
    """FAQ Category create"""
    name: str = Field(..., description="Name")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")


class AdminFaqCategoryUpdate(AdminFaqCategoryCreate):
    """FAQ Category update"""


class AdminFaqQuery(GenericQueryBaseModel):
    """
    FAQ query model
    """
    category_id: Optional[UUID] = Field(None, description="Category ID")


class AdminFaqBase(UUIDBaseModel):
    """
    FAQ base model
    """
    question: str = Field(..., description="Question")
    related_link: Optional[str] = Field(None, serialization_alias="relatedLink", description="Related Link")
    remark: Optional[str] = Field(None, description="Remark")
    created_at: Optional[datetime] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updatedAt", description="Updated at")


class AdminFaqItem(AdminFaqBase):
    """
    FAQ item
    """
    category_name: Optional[str] = Field(None, serialization_alias="categoryName", description="Category name")


class AdminFaqDetail(AdminFaqBase):
    """FAQ detail"""
    answer: str = Field(..., description="Answer")
    description: Optional[str] = Field(None, description="Description")
    category: Optional[AdminFaqCategoryBase] = Field(None, description="Category")


class AdminFaqPages(PaginationBaseResponseModel):
    """FAQ pages"""
    items: Optional[list[AdminFaqItem]] = Field(..., description="Items")


class AdminFaqCreate(BaseModel):
    """FAQ create"""
    category_id: UUID = Field(..., serialization_alias="categoryId", description="Category ID")
    question: str = Field(..., description="Question")
    answer: str = Field(..., description="Answer")
    related_link: Optional[str] = Field(None, serialization_alias="relatedLink", description="Related Link")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")


class AdminFaqUpdate(AdminFaqCreate):
    """FAQ update"""

