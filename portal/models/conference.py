"""
Conference models
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

from portal.libs.database.orm import ModelBase, Base
from .mixins import BaseMixin, SortableMixin


class PortalConference(ModelBase, BaseMixin):
    """Portal Conference Model"""
    title = Column(sa.String(255), nullable=False, comment="Conference title")
    start_date = Column(sa.Date, nullable=False, comment="Conference start date")
    end_date = Column(sa.Date, nullable=False, comment="Conference end date")
    timezone = Column(sa.String(255), nullable=False, comment="Timezone")
    is_active = Column(sa.Boolean, default=True, comment="Is conference active")
    location_id = Column(
        UUID,
        sa.ForeignKey("portal_location.id", ondelete="SET NULL"),
        nullable=True,
        comment="Location ID",
        index=True
    )


class PortalConferenceInstructors(Base, SortableMixin):
    """Portal Conference Instructors Model"""
    conference_id = Column(
        UUID,
        sa.ForeignKey(PortalConference.id, ondelete="CASCADE", name="fk_conference_instructors_conference_id"),
        nullable=False,
        index=True,
        primary_key=True
    )
    instructor_id = Column(
        UUID,
        sa.ForeignKey("portal_instructor.id", ondelete="CASCADE", name="fk_conference_instructors_instructor_id"),
        nullable=False,
        index=True,
        primary_key=True
    )
    is_primary = Column(sa.Boolean, default=False, comment="Is primary instructor")
