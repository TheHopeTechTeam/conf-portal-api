"""
Ticket serializers
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel

from portal.schemas.mixins import JSONStringMixinModel, UUIDBaseModel


class TicketType(UUIDBaseModel, JSONStringMixinModel):
    """
    Ticket type
    """
    name: str = Field(..., description="Ticket type name")


class TicketBase(UUIDBaseModel, JSONStringMixinModel):
    """
    Ticket
    """
    type: TicketType = Field(..., description="Ticket type")
    order_id: UUID = Field(None, description="Order id", serialization_alias="orderId")
    is_redeemed: bool = Field(False, description="Is redeemed", serialization_alias="isRedeemed")
    is_checked_in: bool = Field(False, description="Is checked in", serialization_alias="isCheckedIn")
    checked_in_at: Optional[datetime] = Field(None, description="Checked in at", serialization_alias="checkedInAt")
    identity: Optional[str] = Field(None, description="Identity")
    belong_church: Optional[str] = Field(None, serialization_alias="belongChurch", description="Belong church")


class CheckInRequest(BaseModel):
    """Request body for check-in (scanner sends ticket_id from QR)"""
    ticket_id: UUID = Field(..., description="Ticket ID from QR code", serialization_alias="ticketId")


class CheckInResponse(BaseModel):
    """Check in response"""
    email: Optional[str] = Field(None, description="User email address")
    ticket: Optional[TicketBase] = Field(None, description="Ticket (None when system has no ticket info)")
    success: bool = Field(..., description="Check-in success or failure")
    message: str = Field(..., description="Status message: 報到成功 / 此票券已完成報到 / 此票卷尚未取票 / 系統查無此票券資訊")
    display_name: Optional[str] = Field(None, description="Ticket holder display name", serialization_alias="displayName")
    workshop_registration_status: Optional[str] = Field(
        None,
        description="Workshop status: 已全部報名 / 尚未報名工作坊",
        serialization_alias="workshopRegistrationStatus",
    )

