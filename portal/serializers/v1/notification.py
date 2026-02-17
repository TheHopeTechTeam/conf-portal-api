"""
User notification serializers (list all with read status, mark read)
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from portal.schemas.mixins import UUIDBaseModel


class UserNotificationItem(UUIDBaseModel):
    """Single notification item for current user (notification history + content, with is_read)"""
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    url: Optional[str] = Field(None, description="Notification URL")
    is_read: bool = Field(..., description="Is read", serialization_alias="isRead")
    created_at: datetime = Field(..., description="Created at", serialization_alias="createdAt")


class UserNotificationList(BaseModel):
    """List of all notifications for current user, each with read status"""
    items: list[UserNotificationItem] = Field(..., description="Notification items")
