"""
Workshop models
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

from portal.libs.database.orm import ModelBase, Base
from .mixins import BaseMixin, SortableMixin


class PortalWorkshop(ModelBase, BaseMixin, SortableMixin):
    """Workshop Model"""
    title = Column(sa.String(255), nullable=False, comment="Workshop title")
    start_datetime = Column(sa.TIMESTAMP(timezone=True), nullable=False, comment="Start datetime")
    end_datetime = Column(sa.TIMESTAMP(timezone=True), nullable=False, comment="End datetime")
    timezone = Column(sa.String(255), nullable=False, comment="Timezone")
    conference_id = Column(
        UUID,
        sa.ForeignKey("portal_conference.id", ondelete="CASCADE"),
        nullable=False,
        comment="Conference ID",
        index=True
    )
    location_id = Column(
        UUID,
        sa.ForeignKey("portal_location.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Location ID",
        index=True
    )
    participants_limit = Column(sa.BigInteger, comment="Participants limit")
    slido_url = Column(sa.String(500), comment="Slido URL")


class PortalWorkshopInstructor(Base, SortableMixin):
    """Portal Workshop Instructor Model"""
    workshop_id = Column(
        UUID,
        sa.ForeignKey(PortalWorkshop.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
        primary_key=True
    )
    instructor_id = Column(
        UUID,
        sa.ForeignKey("portal_instructor.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        primary_key=True
    )
    is_primary = Column(sa.Boolean, default=False, comment="Is primary instructor")


class PortalWorkshopRegistration(ModelBase, BaseMixin):
    """Workshop Registration Model"""
    __extra_table_args__ = (
        sa.UniqueConstraint("workshop_id", "user_id"),
    )
    workshop_id = Column(
        UUID,
        sa.ForeignKey(PortalWorkshop.id, ondelete="CASCADE"),
        nullable=False,
        comment="Workshop ID",
        index=True
    )
    user_id = Column(
        UUID,
        sa.ForeignKey("portal_user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User ID",
        index=True
    )
    registered_at = Column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), comment="Registration time")
    unregistered_at = Column(sa.TIMESTAMP(timezone=True), comment="Unregistration time")
