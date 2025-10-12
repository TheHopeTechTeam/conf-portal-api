"""
Account serializers
"""
from typing import Optional

from pydantic import BaseModel, Field

from portal.libs.consts.enums import AuthProvider
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.ticket import TicketBase


class AccountLogin(BaseModel):
    """
    Account login
    """
    login_method: AuthProvider = Field(
        default=AuthProvider.FIREBASE,
        serialization_alias="loginMethod",
        description="Login method"
    )
    firebase_token: str = Field(
        ...,
        serialization_alias="firebaseToken",
        description="Firebase token",
        frozen=True
    )
    device_id: Optional[str] = Field(
        None,
        serialization_alias="deviceId",
        description="Device ID",
        frozen=True
    )


class LoginResponse(UUIDBaseModel):
    """
    Login response
    """
    verified: bool = Field(
        default=False,
        description="Verified"
    )
    first_login: bool = Field(
        default=False,
        serialization_alias="firstLogin",
        description="First login"
    )


class AccountBase(UUIDBaseModel):
    """
    Account
    """
    # google_uid: str = Field(..., serialization_alias="googleUid", description="Google UID")
    phone_number: str = Field(..., serialization_alias="phoneNumber", description="Phone Number")
    email: Optional[str] = Field(default=None, description="Email")
    display_name: Optional[str] = Field(default=None, serialization_alias="displayName", description="Display Name")
    volunteer: Optional[bool] = Field(default=False, description="Volunteer")


class AccountDetail(AccountBase):
    """
    Account detail
    """
    ticket_detail: Optional[TicketBase] = Field(default=None, serialization_alias="ticketDetail", description="Ticket Detail")


class AccountUpdate(BaseModel):
    """
    Account update
    """
    display_name: str = Field(..., serialization_alias="displayName", description="Display Name")
    email: str = Field(..., description="Email")
