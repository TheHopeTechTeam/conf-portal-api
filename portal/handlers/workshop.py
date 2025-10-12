"""
WorkshopHandler
"""
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from asyncpg import UniqueViolationError

from django.core.cache import BaseCache, cache
from django.db import IntegrityError
from redis.asyncio import Redis

from portal.config import settings
# from portal.apps.account.models import Account
# from portal.apps.instructor.models import Instructor
# from portal.apps.location.models import Location
# from portal.apps.workshop.models import WorkshopTimeSlot, Workshop, WorkshopRegistration
from portal.exceptions.responses import APIException, NotFoundException, ResourceExistsException
from portal.handlers.file import FileHandler
from portal.libs.consts.enums import Rendition
from portal.libs.contexts.api_context import APIContext, get_api_context
from portal.libs.contexts.user_context import UserContext, get_user_context
from portal.libs.database import Session, RedisPool
from portal.models import (
    PortalWorkshop,
    PortalWorkshopInstructor,
    PortalWorkshopRegistration,
    PortalInstructor,
    PortalLocation,
)
from portal.serializers.v1.instructor import InstructorBase
from portal.serializers.v1.location import LocationBase
from portal.serializers.v1.workshop import (
    WorkshopBase,
    WorkshopDetail,
    WorkshopSchedule,
    WorkshopScheduleList,
    WorkshopRegistered,
    WorkshopRegisteredList,
)


class WorkshopHandler:
    """WorkshopHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        file_handler: FileHandler,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._file_handler = file_handler
        try:
            self._user_ctx: UserContext = get_user_context()
        except Exception:
            self._user_ctx = None

    async def get_workshop_schedule_list(self) -> WorkshopScheduleList:
        """
        Get the workshop list

        :return:
        """
        workshops: Optional[list[WorkshopBase]] = await (
            self._session.select(
                PortalWorkshop.id,
                PortalWorkshop.title,
                PortalWorkshop.start_datetime,
                PortalWorkshop.end_datetime,
                PortalWorkshop.description,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalLocation.id, sa.String),
                    sa.cast("name", sa.VARCHAR(255)), PortalLocation.name,
                    sa.cast("address", sa.Text), PortalLocation.address,
                    sa.cast("floor", sa.VARCHAR(10)), PortalLocation.floor,
                    sa.cast("room_number", sa.VARCHAR(10)), PortalLocation.room_number,
                ).label("location"),
                PortalWorkshop.slido_url,
                PortalWorkshop.participants_limit,
                sa.case(
                    (sa.func.count(PortalWorkshopRegistration.id) > PortalWorkshop.participants_limit, "TRUE"),
                    else_="FALSE"
                ).label("is_full"),
                PortalWorkshop.timezone
            )
            .outerjoin(PortalWorkshopRegistration, PortalWorkshop.id == PortalWorkshopRegistration.workshop_id)
            .outerjoin(PortalLocation, PortalWorkshop.location_id == PortalLocation.id)
            .where(PortalWorkshop.is_deleted == False)
            .where(PortalLocation.is_deleted == False)
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .group_by(
                PortalWorkshop.id,
                PortalLocation.id,
                PortalWorkshop.participants_limit,
                PortalWorkshop.start_datetime
            )
            .order_by(PortalWorkshop.start_datetime)
            .fetch(as_model=WorkshopBase)
        )
        if not workshops:
            return WorkshopScheduleList(schedule=[])
        schedule_map = defaultdict(list)
        for workshop in workshops:
            start_datetime_with_tz = workshop.start_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
            end_datetime_with_tz = workshop.end_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
            mapping_key = f"{start_datetime_with_tz.isoformat()},{end_datetime_with_tz.isoformat()}"
            location_img = await self._file_handler.get_signed_url_by_resource_id(workshop.location.id)
            workshop.location.image_url = location_img[0] if location_img else None
            if mapping_key not in schedule_map:
                schedule_map[mapping_key] = []
            schedule_map[mapping_key].append(workshop)
        workshop_schedules = []
        for schedule_key, workshops in schedule_map.items():  # type: (str, list[WorkshopBase])
            start_date_str, end_date_str = schedule_key.split(",")
            start_datetime = datetime.fromisoformat(start_date_str)
            end_datetime = datetime.fromisoformat(end_date_str)
            workshop_schedules.append(
                WorkshopSchedule(
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                    workshops=workshops
                )
            )

        return WorkshopScheduleList(schedule=workshop_schedules)

    async def get_workshop_detail(self, workshop_id: uuid.UUID) -> WorkshopDetail:
        """
        Get workshop detail

        :param workshop_id:
        :return:
        """
        workshop: Optional[WorkshopDetail] = await (
            self._session.select(
                PortalWorkshop.id,
                PortalWorkshop.title,
                PortalWorkshop.start_datetime,
                PortalWorkshop.end_datetime,
                PortalWorkshop.description,
                PortalWorkshop.slido_url,
                PortalWorkshop.participants_limit,
                PortalWorkshop.timezone,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalLocation.id, sa.String),
                    sa.cast("name", sa.VARCHAR(255)), PortalLocation.name,
                    sa.cast("address", sa.Text), PortalLocation.address,
                    sa.cast("floor", sa.VARCHAR(10)), PortalLocation.floor,
                    sa.cast("room_number", sa.VARCHAR(10)), PortalLocation.room_number,
                ).label("location"),
                sa.case(
                    (sa.func.count(PortalWorkshopRegistration.id) > PortalWorkshop.participants_limit, sa.text("true")),
                    else_=sa.text("false")
                ).label("is_full"),
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalInstructor.id, sa.String),
                    sa.cast("name", sa.VARCHAR(255)), PortalInstructor.name,
                    sa.cast("title", sa.VARCHAR(255)), PortalInstructor.title,
                    sa.cast("bio", sa.Text), PortalInstructor.bio,
                ).label("instructor"),
            )
            .outerjoin(PortalWorkshopRegistration, PortalWorkshop.id == PortalWorkshopRegistration.workshop_id)
            .outerjoin(PortalLocation, PortalWorkshop.location_id == PortalLocation.id)
            .outerjoin(PortalWorkshopInstructor, PortalWorkshopInstructor.workshop_id == PortalWorkshop.id)
            .outerjoin(PortalInstructor, PortalInstructor.id == PortalWorkshopInstructor.instructor_id)
            .where(PortalWorkshop.id == workshop_id)
            .where(PortalWorkshop.is_deleted == False)
            .where(PortalLocation.is_deleted == False)
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .group_by(
                PortalWorkshop.id,
                PortalWorkshop.participants_limit,
                PortalWorkshop.start_datetime,
                PortalLocation.id,
                PortalInstructor.id,
            )
            .order_by(PortalWorkshop.start_datetime)
            .fetchrow(as_model=WorkshopDetail)
        )
        if not workshop:
            raise NotFoundException(detail=f"Workshop {workshop_id} not found")
        start_datetime_with_tz = workshop.start_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
        end_datetime_with_tz = workshop.end_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
        workshop.start_datetime = start_datetime_with_tz
        workshop.end_datetime = end_datetime_with_tz
        location_img = await self._file_handler.get_signed_url_by_resource_id(workshop.location.id)
        workshop.location.image_url = location_img[0] if location_img else None
        instructor_img = await self._file_handler.get_signed_url_by_resource_id(workshop.instructor.id)
        workshop.instructor.image_url = instructor_img[0] if instructor_img else None
        workshop_img = await self._file_handler.get_signed_url_by_resource_id(workshop.id)
        workshop.image_url = workshop_img[0] if workshop_img else None
        return workshop

    async def check_has_registered_at_timeslot(self, workshop_id: uuid.UUID) -> bool:
        """
        Check has registered at timeslot

        :param workshop:
        :return:
        """

    async def register_workshop(self, workshop_id: uuid.UUID) -> None:
        """
        Register workshop
        :param workshop_id:
        :return:
        """
        if await self.check_has_registered_at_timeslot(workshop_id=workshop_id):
            raise ResourceExistsException(
                detail="You have already registered for this workshop.",
            )

        try:
            await (
                self._session.insert(PortalWorkshopRegistration)
                .values(
                    workshop_id=workshop_id,
                    user=self._user_ctx.user_id,
                    unregistered_at=None,
                )
            )
        except UniqueViolationError:
            raise ResourceExistsException(
                detail="You have already registered for this workshop.",
            )

    async def unregister_workshop(self, workshop_id: uuid.UUID) -> None:
        """
        Unregister workshop

        :param workshop_id:
        :return:
        """

    async def get_registered_workshops(self) -> dict[str, bool]:
        """
        Get registered workshops

        :return:
        """

    async def check_workshop_is_full(self, workshop_id: uuid.UUID) -> bool:
        """
        Check workshop is full
        :param workshop_id:
        :return:
        """
        is_full: bool = await (
            self._session.select(
                sa.case(
                    (sa.func.count(PortalWorkshopRegistration.id) >= PortalWorkshop.participants_limit, True),
                    else_=False
                ).label("is_full")
            )
            .outerjoin(PortalWorkshopRegistration, PortalWorkshop.id == PortalWorkshopRegistration.workshop_id)
            .where(PortalWorkshop.id == workshop_id)
            .where(PortalWorkshop.is_deleted == False)
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .fetchval()
        )
        return is_full


    async def get_my_workshops(self) -> WorkshopRegisteredList:
        """
        Get my workshops

        :return:
        """
