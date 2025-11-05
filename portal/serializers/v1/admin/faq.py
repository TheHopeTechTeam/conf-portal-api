"""
FAQ serializers
"""

from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel


class FaqCategoryBase(UUIDBaseModel):
    """
    FAQ Category base model
    """
    name: str = Field(..., description="Name")


class FaqCategoryItem(FaqCategoryBase):
    """
    FAQ Category item
    """
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")
    created_at: Optional[str] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[str] = Field(None, serialization_alias="updatedAt", description="Updated at")


class FaqCategoryDetail(FaqCategoryItem):
    """FAQ Category detail"""
    pass


class FaqCategoryList(BaseModel):
    """FAQ Category list"""
    categories: list[FaqCategoryBase] = Field(..., description="Categories")


class FaqCategoryCreate(BaseModel):
    """FAQ Category create"""
    name: str = Field(..., description="Name")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")


class FaqCategoryUpdate(FaqCategoryCreate):
    """FAQ Category update"""


class FaqQuery(GenericQueryBaseModel):
    """
    FAQ query model
    """
    category_id: Optional[UUID] = Field(None, serialization_alias="categoryId", description="Category ID")


class FaqBase(UUIDBaseModel):
    """
    FAQ base model
    """
    question: str = Field(..., description="Question")
    related_link: Optional[str] = Field(None, serialization_alias="relatedLink", description="Related Link")
    remark: Optional[str] = Field(None, description="Remark")
    created_at: Optional[str] = Field(None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[str] = Field(None, serialization_alias="updatedAt", description="Updated at")


class FaqItem(FaqBase):
    """
    FAQ item
    """
    category_name: Optional[str] = Field(None, serialization_alias="categoryName", description="Category name")


class FaqDetail(FaqBase):
    """FAQ detail"""
    answer: str = Field(..., description="Answer")
    description: Optional[str] = Field(None, description="Description")
    category: Optional[FaqCategoryBase] = Field(None, description="Category")


class FaqPages(PaginationBaseResponseModel):
    """FAQ pages"""
    items: Optional[list[FaqItem]] = Field(..., description="Items")


class FaqCreate(BaseModel):
    """FAQ create"""
    category_id: UUID = Field(..., serialization_alias="categoryId", description="Category ID")
    question: str = Field(..., description="Question")
    answer: str = Field(..., description="Answer")
    related_link: Optional[str] = Field(None, serialization_alias="relatedLink", description="Related Link")
    remark: Optional[str] = Field(None, description="Remark")
    description: Optional[str] = Field(None, description="Description")


class FaqUpdate(FaqCreate):
    """FAQ update"""

