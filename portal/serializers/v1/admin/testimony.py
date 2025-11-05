"""
Testimony serializers (Admin)
"""

from typing import Optional

from pydantic import Field

from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel


class TestimonyQuery(GenericQueryBaseModel):
    """
    Testimony query model
    """
    share: Optional[bool] = Field(default=None, description="Share permission")


class TestimonyBase(UUIDBaseModel):
    """
    Testimony base model
    """
    name: str = Field(..., description="Name")
    phone_number: Optional[str] = Field(default=None, serialization_alias="phoneNumber", description="Phone number")
    share: bool = Field(default=False, description="Share permission")
    remark: Optional[str] = Field(default=None, description="Remark")
    created_at: Optional[str] = Field(default=None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[str] = Field(default=None, serialization_alias="updatedAt", description="Updated at")


class TestimonyItem(TestimonyBase):
    """Testimony item"""
    message: Optional[str] = Field(..., description="Message")
    description: Optional[str] = Field(default=None, description="Description")


class TestimonyDetail(TestimonyItem):
    """Testimony detail"""


class TestimonyPages(PaginationBaseResponseModel):
    items: Optional[list[TestimonyItem]] = Field(..., description="Items")
