"""
Schema of User model.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from portal.libs.consts.enums import Gender
from portal.schemas.mixins import UUIDBaseModel, BaseMixinModel


class SUserBase(UUIDBaseModel, BaseMixinModel):
    """
    Base schema for User model, containing common fields.
    """
    phone_number: str = Field(..., description="User's phone number")
    email: Optional[str] = Field(None, description="User's email address")
    verified: bool = Field(False, description="Is the user verified")
    is_active: bool = Field(description="Is the user active")
    is_superuser: bool = Field(False, description="Is the user a superuser")
    is_admin: bool = Field(False, description="Can the user access the admin panel")
    last_login_at: Optional[datetime] = Field(None, description="Timestamp of the user's last login")


class SUserDetail(SUserBase):
    """
    Detailed schema for User model, extending UserBase with additional fields.
    """
    display_name: Optional[str] = Field(..., description="User's display name")
    gender: Optional[Gender] = Field(None, description="User's gender")
    is_ministry: bool = Field(False, description="Is the user a ministry")


class SUserSensitive(SUserDetail):
    """
    Schema for User model including sensitive fields.
    """
    password_hash: Optional[str] = Field(None, description="Hashed password for the user")
    salt: Optional[str] = Field(None, description="Salt used for hashing the password")
    password_changed_at: Optional[datetime] = Field(None, description="Timestamp of the user's password last change")
    password_expires_at: Optional[datetime] = Field(None, description="Timestamp of the user's password expiration")


class SUserThirdParty(SUserDetail):
    provider_id: UUID = Field(..., description="Provider ID")
    provider: str = Field(..., description="Provider name")
    provider_uid: str = Field(..., description="Provider UID")
    additional_data: Optional[dict] = Field(None, description="Additional Data from the provider")


class SAuthProvider(UUIDBaseModel):
    """
    Schema for Auth Provider
    """
    name: str = Field(..., description="Provider name")
