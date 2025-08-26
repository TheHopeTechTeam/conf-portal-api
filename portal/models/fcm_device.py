"""
FCM Device models
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from portal.libs.database.orm import ModelBase
from .mixins import BaseMixin


class PortalFcmDevice(ModelBase, BaseMixin):
    """FCM Device Model"""
    device_key = Column(sa.String(255), nullable=False, unique=True, comment="Device Key")
    token = Column(sa.String(255), nullable=False, comment="FCM token")
    expired_at = Column(sa.DateTime(timezone=True), comment="Expiration time")
    additional_data = Column(JSONB, comment="Additional device data")


class PortalFcmUserDevice(ModelBase, BaseMixin):
    """FCM User Device Model"""
    user_id = Column(
        UUID,
        sa.ForeignKey("portal_user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User ID",
        index=True
    )
    device_id = Column(
        UUID,
        sa.ForeignKey(PortalFcmDevice.id, ondelete="CASCADE"),
        nullable=False,
        comment="FCM Device ID",
        index=True
    )
