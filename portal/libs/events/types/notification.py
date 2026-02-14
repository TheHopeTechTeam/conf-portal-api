"""
Event definitions
"""
from uuid import UUID

from portal.libs.events.base import BaseEvent
from portal.serializers.v1.admin.notification import AdminNotificationCreate


class NotificationCreatedEvent(BaseEvent):
    """
    Event emitted when a notification is created and ready to be sent
    """
    notification_id: UUID
    model: AdminNotificationCreate
