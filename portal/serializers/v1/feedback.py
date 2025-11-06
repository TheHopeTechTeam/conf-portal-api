"""
Feedback serializers
"""
from typing import Optional

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """
    FeedbackCreate
    """
    name: str = Field(..., description="Name of the feedback")
    email: Optional[str] = Field(None, description="Email of the feedback")
    message: str = Field(
        ...,
        description="Message of the feedback",
        max_length=200
    )
