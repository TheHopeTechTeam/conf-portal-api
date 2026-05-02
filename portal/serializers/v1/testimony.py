"""
Testimony serializer
"""
from typing import Optional

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel


class TestimonyCreate(BaseModel):
    """
    FeedbackCreate
    """
    name: str = Field(..., description="Name")
    phone_number: Optional[str] = Field(None, description="Phone number")
    share: bool = Field(False, description="Share testimony")
    message: str = Field(..., description="Message")


class TestimonyCreateResponse(UUIDBaseModel):
    """
    FeedbackCreateResponse
    """
