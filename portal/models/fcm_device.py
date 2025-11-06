"""
FCM Device models
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from portal.libs.database.orm import ModelBase, Base
from .mixins import BaseMixin


class PortalFcmDevice(ModelBase, BaseMixin):
    """FCM Device Model"""
    device_key = Column(sa.String(255), nullable=False, unique=True, comment="Device Key")
    token = Column(sa.String(255), nullable=False, comment="FCM token")
    expired_at = Column(sa.DateTime(timezone=True), comment="Expiration time")
    additional_data = Column(JSONB, comment="Additional device data")


class PortalFcmUserDevice(Base):
    """FCM User Device Model"""
    __extra_table_args__ = (
        sa.UniqueConstraint("user_id", "device_id"),
    )
    user_id = Column(
        UUID,
        sa.ForeignKey("portal_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        primary_key=True
    )
    device_id = Column(
        UUID,
        sa.ForeignKey(PortalFcmDevice.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
        primary_key=True
    )
