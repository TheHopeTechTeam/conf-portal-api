"""
Base serializer mixin for all serializers.
"""
import abc
from typing import Any, Optional

import pydantic
from pydantic import BaseModel, Field


class PaginationQueryBaseModel(BaseModel):
    """
    Base serializer mixin for all paginated query models.
    """
    page: int = Field(0, description="Page number")
    page_size: int = Field(10, description="Page size")


class OrderByQueryBaseModel(PaginationQueryBaseModel):
    """
    Base serializer mixin for all order by query models.
    """
    order_by: Optional[str] = Field(None, description="Order by field")
    descending: bool = Field(False, description="Descending order")


class GenericQueryBaseModel(OrderByQueryBaseModel):
    """
    Base serializer mixin for all generic query models.
    """
    deleted: bool = Field(False, description="Deleted items only")


class PaginationBaseResponseModel(BaseModel):
    """
    Base serializer mixin for all paginated response models.
    """
    page: int = Field(..., description="Page number")
    page_size: int = Field(..., description="Page size")
    total: int = Field(..., description="Total number of items")

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, "items"):
            raise ValueError("items field is required")

class DeleteBaseModel(BaseModel):
    """
    Base serializer mixin for all delete models.
    """
    reason: Optional[str] = Field(None, description="Delete reason")
    permanent: bool = Field(False, description="Permanent delete")

    @pydantic.model_validator(mode='after')
    def validate_reason(self):
        """validate reason required if not permanent delete"""
        if not self.permanent and self.reason is None:
            raise ValueError("Reason is required for non-permanent delete")
        return self
