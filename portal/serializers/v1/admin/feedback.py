"""
Feedback serializers (Admin)
"""

from typing import Optional

from pydantic import BaseModel, Field

from portal.libs.consts.enums import FeedbackStatus
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, PaginationBaseResponseModel


class FeedbackQuery(GenericQueryBaseModel):
    """
    Feedback query model
    """
    status: Optional[int] = Field(default=None, description="Feedback status (int value)")


class FeedbackBase(UUIDBaseModel):
    """
    Feedback base model
    """
    name: str = Field(..., description="Name")
    email: Optional[str] = Field(default=None, description="Email")
    status: int = Field(default=FeedbackStatus.PENDING.value, description="Status")
    remark: Optional[str] = Field(default=None, description="Remark")
    created_at: Optional[str] = Field(default=None, serialization_alias="createdAt", description="Created at")
    updated_at: Optional[str] = Field(default=None, serialization_alias="updatedAt", description="Updated at")


class FeedbackItem(FeedbackBase):
    """Feedback item"""
    message: Optional[str] = Field(..., description="Message")
    description: Optional[str] = Field(default=None, description="Description")


class FeedbackDetail(FeedbackItem):
    """Feedback detail"""


class FeedbackPages(PaginationBaseResponseModel):
    items: Optional[list[FeedbackItem]] = Field(..., description="Items")


class FeedbackStatusUpdate(BaseModel):
    """Update feedback status"""
    status: FeedbackStatus = Field(..., description="Status (int value)")
