"""
Ticket serializers
"""
from typing import Optional

from pydantic import Field

from portal.schemas.mixins import JSONStringMixinModel


class TicketBase(JSONStringMixinModel):
    """
    Ticket
    """
    title: str = Field(..., description="Ticket title")
    number: str = Field(..., description="Ticket number")
    ticket_type: str = Field(..., serialization_alias="type", description="Ticket type")
    belong_church: Optional[str] = Field(None, serialization_alias="belongChurch", description="Belong church")
    identity: Optional[str] = Field(None, description="Identity")
    text_color: Optional[str] = Field(None, serialization_alias="textColor", description="Text color")
    background_color: Optional[str] = Field(None, serialization_alias="backgroundColor", description="Background color")
