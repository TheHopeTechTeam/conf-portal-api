"""
Schema of User model.
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from portal.libs.consts.enums import Gender
from portal.schemas.mixins import UUIDBaseModel, BaseMixinModel


class UserBase(UUIDBaseModel, BaseMixinModel):
    """
    Base schema for User model, containing common fields.
    """
    phone_number: str = Field(..., description="User's phone number")
    email: str = Field(..., description="User's email address")
    password_hash: Optional[str] = Field(None, description="Hashed password for the user")
    salt: Optional[str] = Field(None, description="Salt used for hashing the password")
    verified: bool = Field(False, description="Is the user verified")
    is_active: bool = Field(description="Is the user active")
    is_superuser: bool = Field(False, description="Is the user a superuser")
    is_admin: bool = Field(False, description="Can the user access the admin panel")
    password_changed_at: Optional[datetime] = Field(None, description="Timestamp of the user's password last change")
    password_expires_at: Optional[datetime] = Field(None, description="Timestamp of the user's password expiration")
    last_login_at: Optional[datetime] = Field(None, description="Timestamp of the user's last login")


class UserDetail(UserBase):
    """
    Detailed schema for User model, extending UserBase with additional fields.
    """
    display_name: Optional[str] = Field(..., description="User's display name")
    gender: Optional[Gender] = Field(None, description="User's gender")
    is_ministry: bool = Field(False, description="Is the user a ministry")
