"""
Verb serializers
"""

from typing import Optional

from pydantic import Field, BaseModel

from portal.schemas.mixins import UUIDBaseModel


class VerbItem(UUIDBaseModel):
    """VerbItem"""
    action: str = Field(..., description="Action")
    display_name: str = Field(..., serialization_alias="displayName", description="Display name")
    description: Optional[str] = Field(None, description="Description")


class VerbList(BaseModel):
    """VerbList"""
    items: Optional[list[VerbItem]] = Field(..., description="Verbs")
