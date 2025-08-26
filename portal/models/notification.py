"""
Notification models
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

from portal.libs.consts.enums import NotificationStatus
from portal.libs.database.orm import ModelBase
from .mixins import BaseMixin


class PortalNotification(ModelBase, BaseMixin):
    """Notification Model"""
    title = Column(sa.String(255), nullable=False, comment="Notification title")
    message = Column(sa.Text, nullable=False, comment="Notification message")
    url = Column(sa.String(500), comment="Notification URL")
    type = Column(
        sa.Integer,
        nullable=False,
        comment="Notification type"
    )
    status = Column(
        sa.Integer,
        default=NotificationStatus.PENDING.value,
        comment="Notification status"
    )
    failure_count = Column(sa.Integer, default=0, comment="Failure count")
    success_count = Column(sa.Integer, default=0, comment="Success count")


class PortalNotificationHistory(ModelBase, BaseMixin):
    """Notification History Model"""
    __extra_table_args__ = (
        sa.UniqueConstraint("notification_id", "device_id"),
    )
    notification_id = Column(
        UUID,
        sa.ForeignKey(PortalNotification.id, ondelete="CASCADE", name="fk_notification_history_notification_id"),
        nullable=False,
        comment="Notification ID",
        index=True
    )
    device_id = Column(
        UUID,
        sa.ForeignKey("portal_fcm_device.id", ondelete="CASCADE"),
        nullable=False,
        comment="Device ID",
        index=True
    )
    message_id = Column(sa.String(255), comment="FCM message ID")
    exception = Column(sa.Text, comment="Exception message")
    status = Column(
        sa.Integer,
        nullable=False,
        comment="History status"
    )
