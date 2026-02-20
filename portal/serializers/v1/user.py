"""
User serializers
"""
from typing import Optional

from pydantic import BaseModel, Field

from portal.libs.consts.enums import AuthProvider, Gender
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import LoginResponse
from portal.serializers.v1.ticket import TicketBase


class UserLogin(BaseModel):
    """
    User login
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
    device_id: str = Field(
        ...,
        serialization_alias="deviceId",
        description="Device ID",
        frozen=True
    )


class UserBase(UUIDBaseModel):
    """
    User base
    """
    # google_uid: str = Field(..., serialization_alias="googleUid", description="Google UID")
    phone_number: Optional[str] = Field(None, serialization_alias="phoneNumber", description="Phone Number")
    email: Optional[str] = Field(default=None, description="Email")
    display_name: Optional[str] = Field(default=None, serialization_alias="displayName", description="Display Name")
    volunteer: Optional[bool] = Field(default=False, description="Volunteer")


class UserInfo(UserBase):
    """User info"""
    verified: bool = Field(
        default=False,
        description="Verified"
    )
    first_login: bool = Field(
        default=False,
        serialization_alias="firstLogin",
        description="First login"
    )


class UserLoginResponse(LoginResponse):
    """
    Login response
    """
    user: UserInfo = Field(..., description="User info")


class UserDetail(UserBase):
    """
    User detail
    """
    ticket: Optional[TicketBase] = Field(default=None, serialization_alias="ticket", description="Ticket")


class UserUpdate(BaseModel):
    """
    User update
    """
    display_name: str = Field(..., serialization_alias="displayName", description="Display Name")
    # gender: Optional[Gender] = Field(None, description="Gender")
    phone_number: Optional[str] = Field(None, serialization_alias="phoneNumber", description="Phone Number")
