"""
AdminWorkshopHandler
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
from portal.models import PortalWorkshop, PortalWorkshopRegistration, PortalLocation, PortalConference, PortalWorkshopInstructor, PortalInstructor
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.workshop import (
    WorkshopQuery,
    WorkshopDetail,
    WorkshopPageItem,
    WorkshopPages,
    WorkshopCreate,
    WorkshopUpdate,
    WorkshopChangeSequence,
    WorkshopInstructorBase,
    WorkshopInstructorItem,
    WorkshopInstructorsUpdate,
    WorkshopSequenceItem,
    WorkshopInstructors,
)


class AdminWorkshopHandler:
    """AdminWorkshopHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @distributed_trace()
    async def get_workshop_pages(self, query_model: WorkshopQuery) -> WorkshopPages:
        """

        :param query_model:
        :return:
        """
        registered_count_subquery = (
            self._session.select(
                PortalWorkshopRegistration.workshop_id,
                sa.func.count(PortalWorkshopRegistration.id).label("registered_count")
            )
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .group_by(PortalWorkshopRegistration.workshop_id)
            .subquery()
        )

        items, count = await (
            self._session.select(
                PortalWorkshop.id,
                PortalWorkshop.title,
                PortalWorkshop.timezone,
                PortalWorkshop.start_datetime,
                PortalWorkshop.end_datetime,
                PortalWorkshop.participants_limit,
                PortalWorkshop.remark,
                PortalWorkshop.sequence,
                PortalConference.title.label("conference_title"),
                PortalLocation.name.label("location_name"),
                sa.case(
                    (registered_count_subquery.c.registered_count > 0, registered_count_subquery.c.registered_count),
                    else_=0
                ).label("registered_count")
            )
            .outerjoin(registered_count_subquery, PortalWorkshop.id == registered_count_subquery.c.workshop_id)
            .outerjoin(PortalConference, PortalWorkshop.conference_id == PortalConference.id)
            .outerjoin(PortalLocation, PortalWorkshop.location_id == PortalLocation.id)
            .where(PortalConference.is_active == query_model.is_active)
            .where(PortalWorkshop.is_deleted == query_model.deleted)
            .where(query_model.location_id is not None, lambda: PortalWorkshop.location_id == query_model.location_id)
            .where(query_model.conference_id is not None, lambda: PortalWorkshop.conference_id == query_model.conference_id)
            .where(query_model.start_datatime is not None, lambda: PortalWorkshop.start_datetime >= query_model.start_datatime)
            .where(query_model.end_datatime is not None, lambda: PortalWorkshop.end_datetime <= query_model.end_datatime)
            .group_by(
                PortalWorkshop.id,
                PortalConference.title,
                PortalLocation.name,
                registered_count_subquery.c.registered_count
            )
            .order_by_with(
                tables=[PortalWorkshop],
                order_by=query_model.order_by,
                descending=query_model.descending
            )
            .limit(query_model.page_size)
            .offset(query_model.page * query_model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=WorkshopPageItem
            )
        )

        sequence_item_query = (
            self._session.select(
                PortalWorkshop.id,
                PortalWorkshop.sequence
            )
            .outerjoin(PortalConference, PortalWorkshop.conference_id == PortalConference.id)
            .outerjoin(PortalLocation, PortalWorkshop.location_id == PortalLocation.id)
            .where(PortalConference.is_active == query_model.is_active)
            .where(PortalWorkshop.is_deleted == query_model.deleted)
            .where(query_model.location_id is not None, lambda: PortalWorkshop.location_id == query_model.location_id)
            .where(query_model.conference_id is not None, lambda: PortalWorkshop.conference_id == query_model.conference_id)
            .where(query_model.start_datatime is not None, lambda: PortalWorkshop.start_datetime >= query_model.start_datatime)
            .where(query_model.end_datatime is not None, lambda: PortalWorkshop.end_datetime <= query_model.end_datatime)
            .order_by_with(
                tables=[PortalWorkshop],
                order_by=query_model.order_by,
                descending=query_model.descending
            )
            .limit(1)
        )

        # Get previous and next item
        prev_page = query_model.page - 1 if query_model.page > 0 else None
        next_page = query_model.page + 1 if count > query_model.page * query_model.page_size else None

        # Get previous item
        prev_item = None
        if prev_page:
            prev_item = await (
                sequence_item_query
                .offset(prev_page * query_model.page_size)
                .fetchrow(as_model=WorkshopSequenceItem)
            )

        # Get next item
        next_item = None
        if next_page:
            next_item = await (
                sequence_item_query
                .offset(next_page * query_model.page_size)
                .fetchrow(as_model=WorkshopSequenceItem)
            )

        return WorkshopPages(
            page=query_model.page,
            page_size=query_model.page_size,
            total=count,
            items=items,
            prev_item=prev_item,
            next_item=next_item
        )

    @distributed_trace()
    async def get_workshop_by_id(self, workshop_id: uuid.UUID) -> WorkshopDetail:
        """

        :param workshop_id:
        :return:
        """
        item: Optional[WorkshopDetail] = await (
            self._session.select(
                PortalWorkshop.id,
                PortalWorkshop.title,
                PortalWorkshop.timezone,
                PortalWorkshop.start_datetime,
                PortalWorkshop.end_datetime,
                PortalWorkshop.participants_limit,
                PortalWorkshop.remark,
                PortalWorkshop.sequence,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalLocation.id, sa.String),
                    sa.cast("name", sa.VARCHAR(255)), PortalLocation.name,
                ).label("location"),
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalConference.id, sa.String),
                    sa.cast("title", sa.VARCHAR(255)), PortalConference.title,
                ).label("conference"),
                PortalWorkshop.description,
            )
            .outerjoin(PortalLocation, PortalWorkshop.location_id == PortalLocation.id)
            .outerjoin(PortalConference, PortalWorkshop.conference_id == PortalConference.id)
            .where(PortalWorkshop.id == workshop_id)
            .fetchrow(as_model=WorkshopDetail)
        )

        if not item:
            raise NotFoundException(detail=f"Workshop {workshop_id} not found")
        return item

    @distributed_trace()
    async def create_workshop(self, model: WorkshopCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        workshop_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalWorkshop)
                .values(
                    model.model_dump(exclude_none=True),
                    id=workshop_id,
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Workshop {model.title} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=workshop_id)

    @distributed_trace()
    async def update_workshop(self, workshop_id: uuid.UUID, model: WorkshopUpdate) -> None:
        """

        :param workshop_id:
        :param model:
        :return:
        """
        try:
            await (
                self._session.insert(PortalWorkshop)
                .values(
                    model.model_dump(exclude_none=True),
                    id=workshop_id,
                )
                .on_conflict_do_update(
                    index_elements=[PortalWorkshop.id],
                    set_={
                        "updated_at": sa.func.now(),
                        **model.model_dump()
                    }
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Workshop {model.title} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def change_sequence(self, model: WorkshopChangeSequence):
        """

        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalWorkshop)
                .values(sequence=model.another_sequence)
                .where(PortalWorkshop.id == model.id)
                .execute()
            )
            await (
                self._session.update(PortalWorkshop)
                .values(sequence=model.sequence)
                .where(PortalWorkshop.id == model.another_id)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def get_workshop_instructors(self, workshop_id: uuid.UUID) -> WorkshopInstructors:
        """

        :param workshop_id:
        :return:
        """
        items = await (
            self._session.select(
                PortalWorkshopInstructor.instructor_id,
                PortalWorkshopInstructor.is_primary,
                PortalWorkshopInstructor.sequence,
                PortalInstructor.name
            )
            .outerjoin(PortalInstructor, PortalWorkshopInstructor.instructor_id == PortalInstructor.id)
            .where(PortalWorkshopInstructor.workshop_id == workshop_id)
            .order_by(PortalWorkshopInstructor.sequence)
            .fetch(as_model=WorkshopInstructorItem)
        )
        return WorkshopInstructors(items=items)

    @distributed_trace()
    async def update_workshop_instructors(self, workshop_id: uuid.UUID, model: WorkshopInstructorsUpdate) -> None:
        """

        :param workshop_id:
        :param model:
        :return:
        """
        try:
            # Clear existing mappings
            await (
                self._session.delete(PortalWorkshopInstructor)
                .where(PortalWorkshopInstructor.workshop_id == workshop_id)
                .execute()
            )
            # Bulk insert new mappings from payload
            if model.instructors:
                base_epoch = time.time()
                values = []
                for item in model.instructors: # type: WorkshopInstructorBase
                    sequence = base_epoch + (item.sequence * 0.001)
                    values.append(
                        {
                            "workshop_id": workshop_id,
                            "instructor_id": item.instructor_id,
                            "is_primary": item.is_primary,
                            "sequence": sequence,
                        }
                    )
                await (
                    self._session.insert(PortalWorkshopInstructor)
                    .values(values)
                    .on_conflict_do_nothing(index_elements=["workshop_id", "instructor_id"])
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def delete_workshop(self, workshop_id: uuid.UUID, model: DeleteBaseModel) -> None:
        """

        :param workshop_id:
        :param model:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(PortalWorkshop)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(PortalWorkshop.id == workshop_id)
                    .execute()
                )
            else:
                await (
                    self._session.delete(PortalWorkshop)
                    .where(PortalWorkshop.id == workshop_id)
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def restore_workshops(self, model: BulkAction) -> None:
        """

        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalWorkshop)
                .values(is_deleted=False, delete_reason=None)
                .where(PortalWorkshop.id.in_(model.ids))
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
