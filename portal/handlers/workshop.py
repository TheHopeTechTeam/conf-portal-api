"""
WorkshopHandler
"""
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from redis.asyncio import Redis
import pydantic

from portal.config import settings
from portal.exceptions.responses import NotFoundException, ConflictErrorException, BadRequestException
from portal.handlers import AdminFileHandler
from portal.libs.contexts.user_context import UserContext, get_user_context
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.models import (
    PortalConference,
    PortalWorkshop,
    PortalWorkshopInstructor,
    PortalWorkshopRegistration,
    PortalInstructor,
    PortalLocation,
)
from portal.serializers.v1.location import LocationBase
from portal.serializers.v1.user import UserSessionWorkshop
from portal.serializers.v1.workshop import (
    WorkshopBase,
    WorkshopDetail,
    WorkshopSchedule,
    WorkshopScheduleList,
    WorkshopRegistered,
    WorkshopRegisteredList,
    WorkshopTime,
)


class WorkshopHandler:
    """WorkshopHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        file_handler: AdminFileHandler,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._file_handler = file_handler
        self._user_ctx: UserContext = get_user_context()

    @distributed_trace()
    async def get_pass_session_workshops_for_user(
        self,
        user_id: uuid.UUID,
        *,
        is_creative: bool,
        is_leadership: bool,
    ) -> list[UserSessionWorkshop]:
        """
        Registered workshops for the active conference matching is_creative / is_leadership flags.
        Used when building user detail for pass types (e.g. creative-only vs leadership-only rows).
        """

        session_workshops: list[WorkshopBase] = await (
            self._session.select(
                PortalWorkshop.id,
                PortalWorkshop.title,
                PortalWorkshop.start_datetime,
                PortalWorkshop.end_datetime,
                PortalWorkshop.description,
                sa.func.coalesce(
                    sa.case(
                        (
                            PortalLocation.id.is_not(None),
                            sa.func.json_build_object(
                                sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalLocation.id, sa.String),
                                sa.cast("name", sa.VARCHAR(255)), PortalLocation.name,
                                sa.cast("address", sa.Text), PortalLocation.address,
                                sa.cast("floor", sa.VARCHAR(10)), PortalLocation.floor,
                                sa.cast("room_number", sa.VARCHAR(10)), PortalLocation.room_number,
                            )
                        ),
                        else_=None
                    ),
                    sa.null()
                ).label("location"),
                PortalWorkshop.timezone
            )
            .outerjoin(PortalConference, PortalWorkshop.conference_id == PortalConference.id)
            .outerjoin(PortalLocation, PortalWorkshop.location_id == PortalLocation.id)
            .where(PortalWorkshop.is_deleted == sa.false())
            .where(PortalConference.is_active == sa.true())
            .where(PortalWorkshop.is_creative == is_creative)
            .where(PortalWorkshop.is_leadership == is_leadership)
            .group_by(
                PortalWorkshop.id,
                PortalLocation.id,
                PortalWorkshop.participants_limit,
                PortalWorkshop.start_datetime
            )
            .order_by(PortalWorkshop.start_datetime)
            .fetch(as_model=WorkshopBase)
        )
        workshops: list[UserSessionWorkshop] = []
        for workshop in session_workshops:
            start_datetime_with_tz = workshop.start_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
            end_datetime_with_tz = workshop.end_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
            workshop.start_datetime = start_datetime_with_tz
            workshop.end_datetime = end_datetime_with_tz
            if workshop.location:
                location_img = await self._file_handler.get_signed_url_by_resource_id(workshop.location.id)
                workshop.location.image_url = location_img[0] if location_img else None
            workshops.append(
                UserSessionWorkshop(
                    title=workshop.title,
                    start_datetime=workshop.start_datetime,
                    end_datetime=workshop.end_datetime,
                    description=workshop.description,
                    location=workshop.location if workshop.location else None
                )
            )
        return workshops

    @distributed_trace()
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
                sa.func.coalesce(
                    sa.case(
                        (
                            PortalLocation.id.is_not(None),
                            sa.func.json_build_object(
                                sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalLocation.id, sa.String),
                                sa.cast("name", sa.VARCHAR(255)), PortalLocation.name,
                                sa.cast("address", sa.Text), PortalLocation.address,
                                sa.cast("floor", sa.VARCHAR(10)), PortalLocation.floor,
                                sa.cast("room_number", sa.VARCHAR(10)), PortalLocation.room_number,
                            )
                        ),
                        else_=None
                    ),
                    sa.null()
                ).label("location"),
                PortalWorkshop.slido_url,
                PortalWorkshop.participants_limit,
                sa.case(
                    (sa.func.count(PortalWorkshopRegistration.id) > PortalWorkshop.participants_limit, sa.text("true")),
                    else_=sa.text("false")
                ).label("is_full"),
                PortalWorkshop.timezone
            )
            .outerjoin(
                PortalWorkshopRegistration, sa.and_(
                    PortalWorkshop.id == PortalWorkshopRegistration.workshop_id,
                    PortalWorkshopRegistration.unregistered_at.is_(None),
                )
            )
            .outerjoin(PortalLocation, PortalWorkshop.location_id == PortalLocation.id)
            .where(PortalWorkshop.is_deleted == sa.false())
            .where(PortalLocation.is_deleted == sa.false())
            .where(PortalWorkshop.is_creative == sa.false())
            .where(PortalWorkshop.is_leadership == sa.false())
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
            if workshop.location:
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

    @distributed_trace()
    async def get_workshop_detail(self, workshop_id: uuid.UUID) -> WorkshopDetail:
        """
        Get workshop detail

        :param workshop_id:
        :return:
        """
        try:
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
                    sa.func.coalesce(
                        sa.case(
                            (
                                PortalLocation.id.is_not(None),
                                sa.func.json_build_object(
                                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalLocation.id, sa.String),
                                    sa.cast("name", sa.VARCHAR(255)), PortalLocation.name,
                                    sa.cast("address", sa.Text), PortalLocation.address,
                                    sa.cast("floor", sa.VARCHAR(10)), PortalLocation.floor,
                                    sa.cast("room_number", sa.VARCHAR(10)), PortalLocation.room_number,
                                ),
                            ),
                            else_=None
                        ),
                        sa.null()
                    ).label("location"),
                    sa.case(
                        (sa.func.count(PortalWorkshopRegistration.id) > PortalWorkshop.participants_limit, sa.text("true")),
                        else_=sa.text("false")
                    ).label("is_full"),
                    sa.func.coalesce(
                        sa.case(
                            (
                                PortalLocation.id.is_not(None),
                                sa.func.json_build_object(
                                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalInstructor.id, sa.String),
                                    sa.cast("name", sa.VARCHAR(255)), PortalInstructor.name,
                                    sa.cast("title", sa.VARCHAR(255)), PortalInstructor.title,
                                    sa.cast("bio", sa.Text), PortalInstructor.bio,
                                ),
                            ),
                            else_=None
                        ),
                        sa.null()
                    ).label("instructor"),
                )
                .outerjoin(
                    PortalWorkshopRegistration,
                    sa.and_(
                        PortalWorkshop.id == PortalWorkshopRegistration.workshop_id,
                        PortalWorkshopRegistration.unregistered_at.is_(None),
                    )
                )
                .outerjoin(PortalLocation, PortalWorkshop.location_id == PortalLocation.id)
                .outerjoin(PortalWorkshopInstructor, PortalWorkshopInstructor.workshop_id == PortalWorkshop.id)
                .outerjoin(PortalInstructor, PortalInstructor.id == PortalWorkshopInstructor.instructor_id)
                .where(PortalWorkshop.id == workshop_id)
                .where(PortalWorkshop.is_deleted == False)
                .where(PortalLocation.is_deleted == False)
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
        except pydantic.ValidationError as e:
            logger.error(f"Failed to get workshop detail: {e}")
        else:
            if not workshop:
                raise NotFoundException(detail=f"Workshop {workshop_id} not found")
            start_datetime_with_tz = workshop.start_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
            end_datetime_with_tz = workshop.end_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
            workshop.start_datetime = start_datetime_with_tz
            workshop.end_datetime = end_datetime_with_tz
            if workshop.location:
                location_img = await self._file_handler.get_signed_url_by_resource_id(workshop.location.id)
                workshop.location.image_url = location_img[0] if location_img else None
            if workshop.instructor:
                instructor_img = await self._file_handler.get_signed_url_by_resource_id(workshop.instructor.id)
                workshop.instructor.image_url = instructor_img[0] if instructor_img else None
            workshop_img = await self._file_handler.get_signed_url_by_resource_id(workshop.id)
            workshop.image_url = workshop_img[0] if workshop_img else None
            return workshop

    @distributed_trace()
    async def check_has_registered_at_timeslot(self, workshop_id: uuid.UUID) -> bool:
        """
        Check the user has registered at timeslot
        :param workshop_id:
        :return:
        """
        workshop: Optional[WorkshopTime] = await (
            self._session.select(
                PortalWorkshop.start_datetime,
                PortalWorkshop.end_datetime,
                PortalWorkshop.timezone
            )
            .where(PortalWorkshop.id == workshop_id)
            .where(PortalWorkshop.is_deleted == False)
            .fetchrow(as_model=WorkshopTime)
        )
        if not workshop:
            raise NotFoundException(detail=f"Workshop {workshop_id} not found")
        has_registered: bool = await (
            self._session.select(
                sa.case(
                    (sa.func.count(PortalWorkshopRegistration.id) > 0, sa.text("true")),
                    else_=sa.text("false")
                ).label("has_registered")
            )
            .join(PortalWorkshop, PortalWorkshop.id == PortalWorkshopRegistration.workshop_id)
            .where(PortalWorkshopRegistration.user_id == self._user_ctx.user_id)
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .where(PortalWorkshop.is_deleted == False)
            .where(
                sa.or_(
                    sa.and_(
                        PortalWorkshop.start_datetime >= workshop.start_datetime,
                        PortalWorkshop.start_datetime < workshop.end_datetime,
                    ),
                    sa.and_(
                        PortalWorkshop.end_datetime > workshop.start_datetime,
                        PortalWorkshop.end_datetime <= workshop.end_datetime,
                    ),
                    sa.and_(
                        PortalWorkshop.start_datetime <= workshop.start_datetime,
                        PortalWorkshop.end_datetime >= workshop.end_datetime,
                    ),
                )
            )
            .fetchval()
        )
        return has_registered

    @distributed_trace()
    async def register_workshop(self, workshop_id: uuid.UUID) -> None:
        """
        Register workshop
        :param workshop_id:
        :return:
        """
        if await self.check_has_registered_at_timeslot(workshop_id=workshop_id):
            raise ConflictErrorException(detail="You have already registered for this workshop.")
        if await self.check_workshop_is_full(workshop_id=workshop_id):
            raise ConflictErrorException(detail="The workshop is full.")
        try:
            await (
                self._session.insert(PortalWorkshopRegistration)
                .values(
                    workshop_id=workshop_id,
                    user_id=self._user_ctx.user_id
                )
                .on_conflict_do_update(
                    index_elements=["workshop_id", "user_id"],
                    set_={
                        "registered_at": datetime.now(),
                        "unregistered_at": None
                    }
                )
                .execute()
            )
        except UniqueViolationError:
            raise ConflictErrorException(detail="You have already registered for this workshop.")

    @distributed_trace()
    async def unregister_workshop(self, workshop_id: uuid.UUID) -> None:
        """
        Unregister workshop

        :param workshop_id:
        :return:
        """
        registration_id: Optional[uuid.UUID] = await (
            self._session.select(
                PortalWorkshopRegistration.id
            )
            .where(PortalWorkshopRegistration.workshop_id == workshop_id)
            .where(PortalWorkshopRegistration.user_id == self._user_ctx.user_id)
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .fetchval()
        )
        if not registration_id:
            raise ConflictErrorException(detail="Unable to unregister workshop.")
        try:
            await (
                self._session.update(PortalWorkshopRegistration)
                .where(PortalWorkshopRegistration.id == registration_id)
                .values(
                    unregistered_at=datetime.now()
                )
                .execute()
            )
        except Exception as e:
            raise BadRequestException(detail=f"Unregister workshop failed: {e}")

    @distributed_trace()
    async def get_registered_workshops(self) -> dict[str, bool]:
        """
        Get registered workshops
        :return:
        """
        raw_workshops: dict = await (
            self._session.select(
                PortalWorkshop.id,
                sa.case(
                    (sa.func.count(PortalWorkshopRegistration.id) > 0, sa.text("true")),
                    else_=sa.text("false")
                ).label("is_registered")
            )
            .outerjoin(PortalWorkshopRegistration, PortalWorkshop.id == PortalWorkshopRegistration.workshop_id)
            .where(PortalWorkshop.is_deleted == False)
            .where(PortalWorkshopRegistration.user_id == self._user_ctx.user_id)
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .group_by(
                PortalWorkshop.id
            )
            .fetchdict(key="id", value="is_registered")
        )
        registered_workshops: dict[str, bool] = {
            str(workshop_id): bool(is_reg) for workshop_id, is_reg in raw_workshops.items()
        }
        return registered_workshops

    @distributed_trace()
    async def check_workshop_is_full(self, workshop_id: uuid.UUID) -> bool:
        """
        Check workshop is full
        :param workshop_id:
        :return:
        """
        is_full: bool = await (
            self._session.select(
                sa.case(
                    (sa.func.count(PortalWorkshopRegistration.id) >= PortalWorkshop.participants_limit, sa.text("true")),
                    else_=sa.text("false")
                ).label("is_full")
            )
            .outerjoin(PortalWorkshopRegistration, PortalWorkshop.id == PortalWorkshopRegistration.workshop_id)
            .where(PortalWorkshop.id == workshop_id)
            .where(PortalWorkshop.is_deleted == False)
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .group_by(PortalWorkshop.participants_limit)
            .fetchval()
        )
        return is_full

    @distributed_trace()
    async def get_my_workshops(self) -> WorkshopRegisteredList:
        """
        Get my workshops

        :return:
        """
        registered_workshops: WorkshopRegistered = await (
            self._session.select(
                PortalWorkshop.id,
                PortalWorkshop.title,
                PortalWorkshop.start_datetime,
                PortalWorkshop.end_datetime,
                PortalWorkshop.description,
                sa.func.coalesce(
                    sa.case(
                        (
                            PortalLocation.id.is_not(None),
                            sa.func.json_build_object(
                                sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalLocation.id, sa.String),
                                sa.cast("name", sa.VARCHAR(255)), PortalLocation.name,
                                sa.cast("address", sa.Text), PortalLocation.address,
                                sa.cast("floor", sa.VARCHAR(10)), PortalLocation.floor,
                                sa.cast("room_number", sa.VARCHAR(10)), PortalLocation.room_number,
                            ),
                        ),
                        else_=None
                    ),
                    sa.null()
                ).label("location"),
                PortalWorkshop.slido_url,
                PortalWorkshop.participants_limit,
                sa.case(
                    (sa.func.count(PortalWorkshopRegistration.id) > PortalWorkshop.participants_limit, sa.text("true")),
                    else_=sa.text("false")
                ).label("is_full"),
                PortalWorkshop.timezone,
                sa.case(
                    (PortalWorkshopRegistration.unregistered_at.is_(None), sa.text("true")),
                    else_=sa.text("false")
                ).label("is_registered"),
            )
            .outerjoin(PortalWorkshopRegistration, PortalWorkshop.id == PortalWorkshopRegistration.workshop_id)
            .outerjoin(PortalLocation, PortalWorkshop.location_id == PortalLocation.id)
            .where(PortalWorkshop.is_deleted == False)
            .where(PortalLocation.is_deleted == False)
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .where(PortalWorkshopRegistration.user_id == self._user_ctx.user_id)
            .group_by(
                PortalWorkshop.id,
                PortalLocation.id,
                PortalWorkshop.participants_limit,
                PortalWorkshop.start_datetime,
                PortalWorkshopRegistration.unregistered_at
            )
            .order_by(PortalWorkshop.start_datetime)
            .fetch(as_model=WorkshopRegistered)
        )
        my_workshops: list[WorkshopRegistered] = []
        for workshop in registered_workshops:  # type: WorkshopRegistered
            start_datetime_with_tz = workshop.start_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
            end_datetime_with_tz = workshop.end_datetime.astimezone(tz=ZoneInfo(workshop.timezone))
            workshop.start_datetime = start_datetime_with_tz
            workshop.end_datetime = end_datetime_with_tz
            if workshop.location:
                location_img = await self._file_handler.get_signed_url_by_resource_id(workshop.location.id)
                workshop.location.image_url = location_img[0] if location_img else None
            my_workshops.append(workshop)
        return WorkshopRegisteredList(workshops=my_workshops)
