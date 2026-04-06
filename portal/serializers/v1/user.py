"""
User serializers
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from portal.libs.consts.enums import AuthProvider, Gender
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import LoginResponse
from portal.serializers.v1.location import LocationBase
from portal.serializers.v1.ticket import TicketBase


class SendSignInLinkRequest(BaseModel):
    """Request to send login verification (sign-in link) email."""
    email: EmailStr = Field(..., description="Recipient email address")


class SendSignInLinkResponse(BaseModel):
    """Response for send sign-in link (202 Accepted)."""
    message: str = Field(
        default="Sign-in link sent. Please check your email.",
        description="Generic message to avoid leaking email existence",
    )


class UserLocalLogin(BaseModel):
    """User local login"""
    email: str = Field(..., description="Email")
    device_id: str = Field(..., description="Device ID", frozen=True)


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


class UserSessionWorkshop(UUIDBaseModel):
    """
    Registered workshop for a pass-specific session (creative / leadership).
    """
    title: str = Field(..., description="Workshop title")
    start_datetime: datetime = Field(
        ...,
        serialization_alias="startDatetime",
        description="Start datetime (workshop timezone)",
    )
    end_datetime: datetime = Field(
        ...,
        serialization_alias="endDatetime",
        description="End datetime (workshop timezone)",
    )
    description: str = Field(default="", description="Description")
    location: Optional[LocationBase] = Field(
        default=None,
        description="Venue; null if no location",
    )


class UserDetail(UserBase):
    """
    User detail
    """
    ticket: Optional[TicketBase] = Field(
        default=None,
        serialization_alias="ticket",
        description="Primary conference ticket (excludes interpretation receiver add-on)",
    )
    creative_session: Optional[list[UserSessionWorkshop]] = Field(
        default=None,
        serialization_alias="creativeSession",
        description=(
            "Registered creative workshops (is_creative); present only when ticket type "
            "code contains CREATIVE; empty list if none registered"
        ),
    )
    leadership_session: Optional[list[UserSessionWorkshop]] = Field(
        default=None,
        serialization_alias="leadershipSession",
        description=(
            "Registered leadership workshops (is_leadership); present only when ticket type "
            "code contains LEADERSHIP; empty list if none registered"
        ),
    )


class UserUpdate(BaseModel):
    """
    User update
    """
    display_name: str = Field(..., serialization_alias="displayName", description="Display Name")
    # gender: Optional[Gender] = Field(None, description="Gender")
    phone_number: Optional[str] = Field(None, serialization_alias="phoneNumber", description="Phone Number")
