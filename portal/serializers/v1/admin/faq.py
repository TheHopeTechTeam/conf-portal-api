"""
FAQ serializers
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel
from portal.serializers.mixins.base import ChangeSequence


class AdminFaqCategoryBase(UUIDBaseModel, JSONStringMixinModel):
    """
    FAQ Category base model
    """
    name: str = Field(..., description="Name")
    remark: Optional[str] = Field(None, description="Remark")
    sequence: Optional[float] = Field(None, description="Display order (small to large)")
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


class AdminFaqSequenceItem(UUIDBaseModel):
    """FAQ id and sequence for pagination neighbors"""
    sequence: float = Field(..., description="Display order (small to large)")
    category_id: UUID = Field(..., serialization_alias="categoryId", description="Category ID")


class AdminFaqItem(AdminFaqBase):
    """
    FAQ item
    """
    category_id: UUID = Field(..., serialization_alias="categoryId", description="Category ID")
    category_name: Optional[str] = Field(None, serialization_alias="categoryName", description="Category name")
    sequence: float = Field(..., description="Display order within category (small to large)")


class AdminFaqDetail(AdminFaqBase):
    """FAQ detail"""
    answer: str = Field(..., description="Answer")
    description: Optional[str] = Field(None, description="Description")
    category: Optional[AdminFaqCategoryBase] = Field(None, description="Category")


class AdminFaqPages(PaginationBaseResponseModel):
    """FAQ pages"""
    items: Optional[list[AdminFaqItem]] = Field(..., description="Items")
    prev_item: Optional[AdminFaqSequenceItem] = Field(None, serialization_alias="prevItem", description="Previous FAQ in sort order")
    next_item: Optional[AdminFaqSequenceItem] = Field(None, serialization_alias="nextItem", description="Next FAQ in sort order")


class AdminFaqCategoryChangeSequence(ChangeSequence):
    """FAQ category change sequence"""


class AdminFaqChangeSequence(ChangeSequence):
    """FAQ change sequence (same category only)"""


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

