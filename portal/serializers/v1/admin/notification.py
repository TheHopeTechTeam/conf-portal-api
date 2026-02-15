"""
Notification Serializers
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from portal.libs.consts.enums import NotificationMethod, NotificationType, NotificationStatus, NotificationHistoryStatus
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import PaginationBaseResponseModel, GenericQueryBaseModel


class FcmDeviceTokenRow(BaseModel):
    """Row shape for FCM device id + token query (e.g. _resolve_push_targets)."""
    id: UUID = Field(..., description="FCM device ID")
    token: str = Field(..., description="FCM device token")


class AdminNotificationCreate(BaseModel):
    """Create notification request"""
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    url: Optional[str] = Field(None, description="Notification URL")
    method: NotificationMethod = Field(..., description="Notification method (PUSH or EMAIL)")
    type: NotificationType = Field(
        ...,
        description="Notification type (INDIVIDUAL, MULTIPLE, or SYSTEM for broadcast to all FCM devices in DB)",
    )
    dry_run: bool = Field(False, description="If true, resolve targets and mark as dry run without sending")
    user_ids: Optional[list[UUID]] = Field(None, description="User IDs for multiple notification")


class AdminNotificationItem(UUIDBaseModel):
    """Notification item"""
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    url: Optional[str] = Field(None, description="Notification URL")
    method: int = Field(..., description="Notification method")
    type: int = Field(..., description="Notification type")
    status: int = Field(..., description="Notification status")
    failure_count: int = Field(..., description="Failure count")
    success_count: int = Field(..., description="Success count")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")


class AdminNotificationHistoryItem(UUIDBaseModel):
    """Notification history item with user info"""
    notification_id: UUID = Field(..., description="Notification ID")
    device_id: UUID = Field(..., description="Device ID")
    message_id: Optional[str] = Field(None, description="FCM message ID")
    exception: Optional[str] = Field(None, description="Exception message")
    status: int = Field(..., description="History status")
    is_read: bool = Field(..., description="Is read")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")
    # User info from join
    user_id: Optional[UUID] = Field(None, description="User ID")
    user_email: Optional[str] = Field(None, description="User email")
    user_display_name: Optional[str] = Field(None, description="User display name")
    user_phone_number: Optional[str] = Field(None, description="User phone number")


class AdminNotificationHistoryQuery(GenericQueryBaseModel):
    """Notification history query"""
    notification_id: Optional[UUID] = Field(None, description="Filter by notification ID")
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    status: Optional[NotificationHistoryStatus] = Field(None, description="Filter by status")


class AdminNotificationHistoryPages(PaginationBaseResponseModel):
    """Notification history pages"""
    items: list[AdminNotificationHistoryItem] = Field(..., description="Items")


class AdminNotificationQuery(GenericQueryBaseModel):
    """Notification query"""
    method: Optional[NotificationMethod] = Field(None, description="Filter by method")
    type: Optional[NotificationType] = Field(None, description="Filter by type")
    status: Optional[NotificationStatus] = Field(None, description="Filter by status")


class AdminNotificationPages(PaginationBaseResponseModel):
    """Notification pages"""
    items: list[AdminNotificationItem] = Field(..., description="Items")
