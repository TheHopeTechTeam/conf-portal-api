"""
Event Info models
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

from portal.libs.database.orm import ModelBase
from .mixins import BaseMixin, SortableMixin


class PortalEventSchedule(ModelBase, BaseMixin, SortableMixin):
    """Event Schedule Model"""
    conference_id = Column(
        UUID,
        sa.ForeignKey("portal_conference.id", ondelete="CASCADE"),
        nullable=False,
        comment="Conference ID",
        index=True
    )
    title = Column(sa.String(255), nullable=False, comment="Event title")
    description = Column(sa.Text, comment="Event description")
    start_datetime = Column(sa.TIMESTAMP(timezone=True), nullable=False, comment="Start DateTime")
    end_datetime = Column(sa.TIMESTAMP(timezone=True), nullable=False, comment="End DateTime")
    text_color = Column(sa.String(7), comment="Text color in hex format")
    background_color = Column(sa.String(7), comment="Background color in hex format")
