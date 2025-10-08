"""
User Serializers
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from portal.libs.consts.enums import Gender
from portal.schemas.user import SUserDetail
from portal.serializers.mixins import PaginationBaseResponseModel, GenericQueryBaseModel


class UserQuery(GenericQueryBaseModel):
    """UserQuery"""
    verified: Optional[bool] = Field(None, description="Is the user verified")
    is_active: Optional[bool] = Field(None, description="Is the user active")
    is_superuser: Optional[bool] = Field(None, description="Is the user a superuser")
    is_admin: Optional[bool] = Field(None, description="Can the user access the admin panel")
    is_ministry: Optional[bool] = Field(None, description="Is the user a ministry")
    gender: Optional[Gender] = Field(None, description="User's gender")


class UserTableItem(SUserDetail):
    """UserTableItem"""
    pass


class UserItem(SUserDetail):
    """UserItem"""
    pass


class UserPages(PaginationBaseResponseModel):
    """UserPages"""
    items: Optional[list[UserTableItem]] = Field(..., description="Items")


class UserCreate(BaseModel):
    """UserCreate"""
    phone_number: str = Field(..., description="User's phone number")
    email: str = Field(..., description="User's email address")
    verified: bool = Field(False, description="Is the user verified")
    is_active: bool = Field(True, description="Is the user active")
    is_superuser: bool = Field(False, description="Is the user a superuser")
    is_admin: bool = Field(False, description="Can the user access the admin panel")
    display_name: Optional[str] = Field(None, description="User's display name")
    gender: Optional[Gender] = Field(Gender.UNKNOWN, description="User's gender")
    is_ministry: bool = Field(False, description="Is the user a ministry")
    remark: Optional[str] = Field(None, description="Remark")


class UserUpdate(UserCreate):
    """UserUpdate"""
    pass


class UserBulkDelete(BaseModel):
    """UserBulkDelete"""
    ids: list[UUID] = Field(..., description="User IDs to delete")
