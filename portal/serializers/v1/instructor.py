"""
Instructor serializers
"""
from typing import Optional

from pydantic import Field

from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel


class InstructorBase(UUIDBaseModel, JSONStringMixinModel):
    """
    Instructor base model
    """
    name: str = Field(..., description="Name")
    title: Optional[str] = Field(None, description="Title")
    bio: str = Field(..., description="Bio")
    image_url: Optional[str] = Field(None, serialization_alias="imageUrl", description="Image URL")
