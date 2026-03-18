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
    code: str = Field(..., description="Ticket type code")


class TicketBase(UUIDBaseModel, JSONStringMixinModel):
    """
    Ticket
    """
    type: TicketType = Field(..., description="Ticket type")
    has_interpretation_receiver: Optional[bool] = Field(
        None,
        serialization_alias="hasInterpretationReceiver",
        description="Whether the user also holds an Interpretation Receiver (口譯機) ticket",
    )
    interpretation_receiver_checked_in: Optional[bool] = Field(
        None,
        serialization_alias="interpretationReceiverCheckedIn",
        description="Whether Interpretation Receiver (口譯機) has been collected (checked in); null if no IR ticket",
    )
    order_id: UUID = Field(None, description="Order id", serialization_alias="orderId")
    is_redeemed: bool = Field(False, description="Is redeemed", serialization_alias="isRedeemed")
    is_checked_in: bool = Field(False, description="Is checked in", serialization_alias="isCheckedIn")
    checked_in_at: Optional[datetime] = Field(None, description="Checked in at", serialization_alias="checkedInAt")
    identity: Optional[str] = Field(None, description="Identity")
    belong_church: Optional[str] = Field(None, serialization_alias="belongChurch", description="Belong church")


class CheckInRequest(BaseModel):
    """
    Main conference ticket ID from QR for both flows.
    When interpretation_receiver is false: check in this main ticket.
    When true: check in the holder's Interpretation Receiver (口譯機) ticket (same main ticket ID).
    """
    ticket_id: UUID = Field(..., description="Main ticket ID from QR code", serialization_alias="ticketId")
    interpretation_receiver: bool = Field(
        False,
        serialization_alias="interpretationReceiver",
        description="If true, redeem IR (口譯機) using this main ticket's holder; if false, main pass check-in",
    )


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

