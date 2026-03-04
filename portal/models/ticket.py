"""
Ticket models
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql.base import UUID

from portal.libs.database.orm import ModelBase
from .mixins import AuditCreatedMixin, BaseMixin


class PortalTicketType(ModelBase, AuditCreatedMixin):
    """
    Ticket Type Model
    code mapping:
        CREATIVE_PASS_SINGLE
        CREATIVE_PASS_DOUBLE
        INTERPRETATION_RECEIVER
        LEADERSHIP_PASS_SINGLE
        LEADERSHIP_PASS_DOUBLE
        ONLINE_PASS_SINGLE
        REGULAR_PASS_SEVEN
        REGULAR_PASS_SINGLE
        REGULAR_PASS_DOUBLE
    """
    name = Column(sa.String(64), nullable=False, unique=True, comment="Ticket type name")
    code = Column(sa.String(32), unique=True, comment="Ticket type code")


class PortalUserTicket(ModelBase, BaseMixin):
    """User Ticket Model"""
    ticket_type_id = Column(UUID, sa.ForeignKey("portal_ticket_type.id", ondelete="CASCADE"), nullable=False, comment="Ticket type id")
    order_id = Column(UUID, nullable=False, comment="Order id")
    user_id = Column(UUID, sa.ForeignKey("portal_user.id", ondelete="CASCADE"), nullable=False, comment="User id")
    is_redeemed = Column(sa.Boolean, default=False, comment="Is redeemed")
    is_checked_in = Column(sa.Boolean, default=False, comment="Is checked in")
    checked_in_at = Column(sa.TIMESTAMP(timezone=True), comment="Checked in at")
    identity = Column(sa.String(32), comment="Identity")
    belong_church = Column(sa.String(64), comment="Belong church")
