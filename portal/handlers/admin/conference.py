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
from portal.models import PortalConference, PortalLocation, PortalConferenceInstructors
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.conference import (
    ConferenceQuery,
    ConferencePages,
    ConferenceItem,
    ConferenceDetail,
    ConferenceCreate,
    ConferenceUpdate,
    ConferenceInstructorsUpdate,
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

    async def get_conference_pages(self, model: ConferenceQuery) -> ConferencePages:
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
                as_model=ConferenceItem
            )
        )
        return ConferencePages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    async def get_conference_by_id(self, conference_id: uuid.UUID) -> ConferenceDetail:
        """

        :param conference_id:
        :return:
        """
        item: Optional[ConferenceDetail] = await (
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
            .fetchrow(as_model=ConferenceDetail)
        )
        if not item:
            raise NotFoundException(detail=f"Conference {conference_id} not found")

        return item

    async def create_conference(self, model: ConferenceCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        conference_id = uuid.uuid4()
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
        except Exception:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
            )
        else:
            return UUIDBaseModel(id=conference_id)

    @distributed_trace()
    async def update_conference(self, conference_id: uuid.UUID, model: ConferenceUpdate) -> None:
        """

        :param conference_id:
        :param model:
        :return:
        """
        try:
            await (
                self._session.insert(PortalConference)
                .values(
                    model.model_dump(exclude_none=True),
                    id=conference_id,
                )
                .on_conflict_do_update(
                    index_elements=[PortalConference.id],
                    set_=model.model_dump(),
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Conference {model.title} already exists",
                debug_detail=str(e),
            )
        except Exception:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
            )

    @distributed_trace()
    async def update_conference_instructors(self, conference_id: uuid.UUID, model: ConferenceInstructorsUpdate) -> None:
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
                    sequence = base_epoch + (item.sequence * 0.001)
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
