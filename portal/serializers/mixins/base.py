"""
Base serializer mixin for all serializers.
"""
import abc
from typing import Any, Optional

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


class PaginationBaseResponseModel(BaseModel, abc.ABC):
    """
    Base serializer mixin for all paginated response models.
    """
    page: int = Field(..., description="Page number")
    page_size: int = Field(..., description="Page size")
    total: int = Field(..., description="Total number of items")

    @property
    @abc.abstractmethod
    def items(self) -> Optional[list[Any]]:
        """
        Items in the current page
        """
