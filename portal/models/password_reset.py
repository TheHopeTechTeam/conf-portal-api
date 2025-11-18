"""
Model of the passwrod reset token table
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

from portal.libs.database.orm import ModelBase
from .mixins import AuditCreatedAtMixin, AuditUpdatedAtMixin


class PortalPasswordResetToken(ModelBase, AuditCreatedAtMixin, AuditUpdatedAtMixin):
    """Password Reset Token Model"""
    user_id = Column(
        UUID,
        sa.ForeignKey("portal_user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User ID",
        index=True
    )
    token = Column(sa.String(255), nullable=False, index=True, comment="Reset token")
    token_hash = Column(sa.String(512), nullable=False, comment="Hashed token for verification")
    expires_at = Column(sa.TIMESTAMP(timezone=True), nullable=False, comment="Token expiration time", index=True)
    used_at = Column(sa.TIMESTAMP(timezone=True), nullable=True, comment="Token used time")
    ip_address = Column(sa.String(45), nullable=True, comment="IP address when token was created")
    user_agent = Column(sa.String(512), nullable=True, comment="User agent when token was created")
