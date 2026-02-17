"""
Ticket serializers (admin - user ticket check-in)
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TicketCheckInResponse(BaseModel):
    """Response for POST ticket check-in"""

    id: UUID = Field(..., description="Ticket id")
    ticket_type_name: Optional[str] = Field(None, description="Ticket type name", serialization_alias="ticketTypeName")
    owner_email: Optional[str] = Field(None, description="Owner email", serialization_alias="ownerEmail")
    owner_name: Optional[str] = Field(None, description="Owner name", serialization_alias="ownerName")
    is_checked_in: bool = Field(..., description="Is checked in", serialization_alias="isCheckedIn")
    updated_at: Optional[datetime] = Field(None, description="Last updated at", serialization_alias="updatedAt")
    message: Optional[str] = Field(None, description="API message")
