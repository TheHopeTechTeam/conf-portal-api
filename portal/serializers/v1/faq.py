"""
FAQ serializers
"""
import uuid
from typing import Optional

from pydantic import Field, BaseModel, field_serializer

from portal.schemas.mixins import UUIDBaseModel


class FaqCategoryBase(UUIDBaseModel):
    """
    FAQ category base model
    """
    name: str = Field(..., description="Name")
    description: Optional[str] = Field(..., description="Description")


class FaqCategoryList(BaseModel):
    """
    FAQ category list model
    """
    categories: list[FaqCategoryBase] = Field(..., description="Categories")


class FaqBase(UUIDBaseModel):
    """
    FAQ base model
    """
    category_id: uuid.UUID = Field(..., serialization_alias="categoryId", description="Category ID")
    question: str = Field(..., description="Question")
    answer: str = Field(..., description="Answer")
    related_link: Optional[str] = Field(default=None, serialization_alias="relatedLink", description="Related Link")

    @field_serializer("category_id")
    def serialize_category_id(self, value: uuid.UUID, _info) -> str:
        """

        :param value:
        :param _info:
        :return:
        """
        return str(value)


class FaqList(BaseModel):
    """
    FAQ list model
    """
    faqs: list[FaqBase] = Field(..., description="FAQs")
