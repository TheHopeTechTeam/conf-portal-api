"""
Ticket type serializers (admin)
"""
from uuid import UUID

from pydantic import BaseModel, Field


class TicketTypeListItem(BaseModel):
    """Ticket type item for list response"""
    id: UUID = Field(..., description="Ticket type id")
    name: str = Field(..., description="Ticket type name")


class TicketTypeListResponse(BaseModel):
    """Response for GET ticket-type list"""
    items: list[TicketTypeListItem] = Field(default_factory=list, description="Ticket types")
