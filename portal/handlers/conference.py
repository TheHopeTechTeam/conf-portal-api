"""
ConferenceHandler
"""
import uuid
from typing import Optional

import sqlalchemy as sa

# from portal.apps.conference.models import Conference
# from portal.apps.location.models import Location
from portal.handlers.file import FileHandler
from portal.libs.consts.enums import Rendition
from portal.libs.database import Session
from portal.serializers.v1.conference import ConferenceBase, ConferenceDetail, ConferenceList
from portal.serializers.v1.instructor import InstructorBase
from portal.serializers.v1.location import LocationBase
from portal.models.conference import PortalConference, PortalConferenceInstructors
from portal.models.location import PortalLocation
from portal.models.instructor import PortalInstructor


class ConferenceHandler:
    """ConferenceHandler"""

    def __init__(
        self,
        session: Session,
        file_handler: FileHandler,
    ):
        self._session = session
        self._file_handler = file_handler

    async def get_conferences(self) -> ConferenceList:
        """
        Get conference
        :return:
        """
        conferences: list[ConferenceBase] = await (
            self._session.select(
                PortalConference.id,
                PortalConference.title,
                PortalConference.start_date,
                PortalConference.end_date,
            )
            .where(PortalConference.is_deleted == False)  # noqa
            .order_by(PortalConference.start_date.desc())
            .fetch(as_model=ConferenceBase)
        )
        return ConferenceList(conferences=conferences)

    async def get_active_conference(self) -> ConferenceDetail:
        """
        Get an active conference
        :return:
        """
        conference_id: Optional[uuid.UUID] = await (
            self._session.select(PortalConference.id)
            .where(PortalConference.is_deleted == False)
            .where(PortalConference.is_active == True)
            .fetchval()
        )
        if not conference_id:
            raise ValueError("No active conference found")
        active_obj = await self.get_conference_detail(conference_id=conference_id)
        return active_obj

    async def get_conference_detail(self, conference_id: uuid.UUID) -> ConferenceDetail:
        """
        Get conference detail
        :param conference_id:
        :return:
        """
        instructor_cte = (
            self._session.select(
                PortalInstructor.id,
                PortalInstructor.name,
                PortalInstructor.title,
                PortalInstructor.bio
            )
            .where(PortalInstructor.is_deleted == False)
            .order_by(PortalInstructor.sequence)
            .cte(name="instructor_cte")
        )
        conference: ConferenceDetail = await (
            self._session.select(
                PortalConference.id,
                PortalConference.title,
                PortalConference.description,
                PortalConference.start_date,
                PortalConference.end_date,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalLocation.id, sa.String),
                    sa.cast("name", sa.VARCHAR(255)), PortalLocation.name,
                    sa.cast("address", sa.Text), PortalLocation.address,
                    sa.cast("floor", sa.VARCHAR(10)), PortalLocation.floor,
                ).label("location"),
                sa.func.array_agg(
                    sa.func.json_build_object(
                        sa.cast("id", sa.VARCHAR(40)), sa.cast(instructor_cte.c.id, sa.String),
                        sa.cast("name", sa.VARCHAR(255)), instructor_cte.c.name,
                        sa.cast("title", sa.VARCHAR(255)), instructor_cte.c.title,
                        sa.cast("bio", sa.Text), instructor_cte.c.bio,
                    )
                ).label("instructors")
            )
            .outerjoin(PortalLocation, PortalConference.location_id == PortalLocation.id)
            .outerjoin(PortalConferenceInstructors, PortalConferenceInstructors.conference_id == PortalConference.id)
            .outerjoin(instructor_cte, instructor_cte.c.id == PortalConferenceInstructors.instructor_id)
            .where(PortalConference.id == conference_id)
            .where(PortalConference.is_deleted == False)
            .where(PortalLocation.is_deleted == False)
            .group_by(
                PortalConference.id,
                PortalLocation.id,
            )
            .fetchrow(as_model=ConferenceDetail)
        )
        location_img = await self._file_handler.get_signed_url_by_resource_id(conference.location.id)
        conference.location.image_url = location_img[0] if location_img else None
        for instructor in conference.instructors:
            instructor_img = await self._file_handler.get_signed_url_by_resource_id(instructor.id)
            instructor.image_url = instructor_img[0] if instructor_img else None
        return conference
