"""
AdminConferenceHandler
"""
import time
import uuid
from typing import Optional

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import NotFoundException, ConflictErrorException, ApiBaseException
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalConference, PortalLocation, PortalConferenceInstructors, PortalInstructor
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.conference import (
    AdminConferenceQuery,
    AdminConferencePages,
    AdminConferenceItem,
    AdminConferenceDetail,
    AdminConferenceCreate,
    AdminConferenceUpdate,
    AdminConferenceInstructorsUpdate,
    AdminConferenceList,
    AdminConferenceBase,
    AdminConferenceInstructors,
    AdminConferenceInstructorItem,
)


class AdminConferenceHandler:
    """AdminConferenceHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @distributed_trace()
    async def get_conference_pages(self, model: AdminConferenceQuery) -> AdminConferencePages:
        """

        :param model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalConference.id,
                PortalConference.title,
                PortalConference.start_date,
                PortalConference.end_date,
                PortalConference.is_active,
                PortalConference.remark,
                PortalConference.description,
                PortalConference.created_at,
                PortalConference.updated_at,
                sa.func.coalesce(PortalLocation.name, sa.text("NULL")).label("location_name"),
            )
            .outerjoin(PortalLocation, PortalConference.location_id == PortalLocation.id)
            .where(PortalConference.is_deleted == model.deleted)
            .where(model.is_active is not None, lambda: PortalConference.is_active == model.is_active)
            .where(
                model.keyword is not None, lambda: sa.or_(
                    PortalConference.title.ilike(f"%{model.keyword}%"),
                    PortalConference.remark.ilike(f"%{model.keyword}%"),
                )
            )
            .order_by_with(
                tables=[PortalConference],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=AdminConferenceItem
            )
        )
        return AdminConferencePages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def get_conference_list(self) -> AdminConferenceList:
        """

        :return:
        """
        items = await (
            self._session.select(
                PortalConference.id,
                PortalConference.title,
            )
            .where(PortalConference.is_deleted == False)
            .order_by(PortalConference.start_date.desc())
            .fetch(as_model=AdminConferenceBase)
        )
        return AdminConferenceList(items=items)

    @distributed_trace()
    async def get_active_conference(self) -> AdminConferenceItem:
        """

        :return:
        """
        item: Optional[AdminConferenceItem] = await (
            self._session.select(
                PortalConference.id,
                PortalConference.title,
                PortalConference.start_date,
                PortalConference.end_date,
                PortalConference.is_active,
                PortalConference.remark,
                PortalConference.description,
                PortalConference.created_at,
                PortalConference.updated_at,
                sa.func.coalesce(PortalLocation.name, sa.text("NULL")).label("location_name"),
            )
            .outerjoin(PortalLocation, PortalConference.location_id == PortalLocation.id)
            .where(PortalConference.is_active == True)
            .order_by(PortalConference.start_date)
            .fetchrow(as_model=AdminConferenceItem)
        )
        if not item:
            raise NotFoundException(detail="No active conference found")
        return item

    @distributed_trace()
    async def get_conference_by_id(self, conference_id: uuid.UUID) -> AdminConferenceDetail:
        """

        :param conference_id:
        :return:
        """
        item: Optional[AdminConferenceDetail] = await (
            self._session.select(
                PortalConference.id,
                PortalConference.title,
                PortalConference.start_date,
                PortalConference.end_date,
                PortalConference.is_active,
                PortalConference.remark,
                PortalConference.description,
                PortalConference.created_at,
                PortalConference.updated_at,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalLocation.id, sa.String),
                    sa.cast("name", sa.VARCHAR(255)), PortalLocation.name,
                ).label("location"),
            )
            .outerjoin(PortalLocation, PortalConference.location_id == PortalLocation.id)
            .where(PortalConference.id == conference_id)
            .fetchrow(as_model=AdminConferenceDetail)
        )
        if not item:
            raise NotFoundException(detail=f"Conference {conference_id} not found")

        return item

    @distributed_trace()
    async def create_conference(self, model: AdminConferenceCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        conference_id = uuid.uuid4()
        active_conference = await self.get_active_conference()
        if model.is_active and active_conference:
            raise ConflictErrorException(detail="Only allowed one active conference at a time.")
        try:
            await (
                self._session.insert(PortalConference)
                .values(
                    model.model_dump(exclude_none=True),
                    id=conference_id,
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Conference {model.title} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=conference_id)

    @distributed_trace()
    async def update_conference(self, conference_id: uuid.UUID, model: AdminConferenceUpdate) -> None:
        """

        :param conference_id:
        :param model:
        :return:
        """
        active_conference = await self.get_active_conference()
        if conference_id != active_conference.id and model.is_active:
            raise ConflictErrorException(detail="Only allowed one active conference at a time.")
        try:
            await (
                self._session.insert(PortalConference)
                .values(
                    model.model_dump(exclude_none=True),
                    id=conference_id,
                )
                .on_conflict_do_update(
                    index_elements=[PortalConference.id],
                    set_={
                        "updated_at": sa.func.now(),
                        **model.model_dump()
                    },
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Conference {model.title} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def get_conference_instructors(self, conference_id: uuid.UUID) -> AdminConferenceInstructors:
        """

        :param conference_id:
        :return:
        """
        items = await (
            self._session.select(
                PortalConferenceInstructors.instructor_id,
                PortalConferenceInstructors.is_primary,
                PortalConferenceInstructors.sequence,
                PortalInstructor.name
            )
            .outerjoin(PortalInstructor, PortalConferenceInstructors.instructor_id == PortalInstructor.id)
            .where(PortalConferenceInstructors.conference_id == conference_id)
            .order_by(PortalConferenceInstructors.sequence)
            .fetch(as_model=AdminConferenceInstructorItem)
        )
        return AdminConferenceInstructors(items=items)

    @distributed_trace()
    async def update_conference_instructors(self, conference_id: uuid.UUID, model: AdminConferenceInstructorsUpdate) -> None:
        """

        :param conference_id:
        :param model:
        :return:
        """
        try:
            # Clear existing mappings
            await (
                self._session.delete(PortalConferenceInstructors)
                .where(PortalConferenceInstructors.conference_id == conference_id)
                .execute()
            )
            # Bulk insert new mappings from payload
            if model.instructors:
                base_epoch = time.time()
                values = []
                for item in model.instructors:
                    sequence = base_epoch + (item.sequence * 0.001) if isinstance(item.sequence, int) else item.sequence
                    values.append(
                        {
                            "conference_id": conference_id,
                            "instructor_id": item.instructor_id,
                            "is_primary": item.is_primary,
                            "sequence": sequence,
                        }
                    )
                await (
                    self._session.insert(PortalConferenceInstructors)
                    .values(values)
                    .on_conflict_do_nothing(index_elements=["conference_id", "instructor_id"])
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def delete_conference(self, conference_id: uuid.UUID, model: DeleteBaseModel) -> None:
        """

        :param conference_id:
        :param model:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(PortalConference)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(PortalConference.id == conference_id)
                    .execute()
                )
            else:
                await (
                    self._session.delete(PortalConference)
                    .where(PortalConference.id == conference_id)
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def restore_conferences(self, model: BulkAction) -> None:
        """

        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalConference)
                .where(PortalConference.id.in_(model.ids))
                .values(is_deleted=False)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
