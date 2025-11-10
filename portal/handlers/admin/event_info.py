"""
AdminEventInfoHandler
"""
import uuid
from typing import Optional

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import NotFoundException, ConflictErrorException, ApiBaseException
from portal.libs.database import Session, RedisPool
from portal.models import PortalEventSchedule, PortalConference
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.admin.event_info import EventInfoList, EventInfoItem, EventInfoDetail, EventInfoCreate, EventInfoUpdate


class AdminEventInfoHandler:
    """AdminEventInfoHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    async def get_event_info_list(self, conference_id: uuid.UUID) -> EventInfoList:
        """

        :param conference_id:
        :return:
        """
        items: Optional[list[EventInfoItem]] = await (
            self._session.select(
                PortalEventSchedule.id,
                PortalEventSchedule.title,
                PortalEventSchedule.start_datetime,
                PortalEventSchedule.end_datetime,
                PortalEventSchedule.timezone,
                PortalEventSchedule.text_color,
                PortalEventSchedule.background_color
            )
            .where(
                sa.and_(
                    PortalEventSchedule.is_deleted.is_(False),
                    PortalEventSchedule.conference_id == conference_id,
                )
            )
            .order_by(PortalEventSchedule.start_datetime.asc())
            .fetch(as_model=EventInfoItem)
        )

        if not items:
            return EventInfoList(items=[])

        return EventInfoList(items=items)

    async def get_event_info_by_id(self, event_id: uuid.UUID) -> EventInfoDetail:
        """

        :param event_id:
        :return:
        """
        item: Optional[EventInfoDetail] = await (
            self._session.select(
                PortalEventSchedule.id,
                PortalEventSchedule.title,
                PortalEventSchedule.start_datetime,
                PortalEventSchedule.end_datetime,
                PortalEventSchedule.timezone,
                PortalEventSchedule.text_color,
                PortalEventSchedule.background_color,
                PortalEventSchedule.remark,
                PortalEventSchedule.description,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(4)), PortalConference.id,
                    sa.cast("title", sa.VARCHAR(8)), PortalConference.title
                ).label('conference'),
            )
            .outerjoin(PortalConference, PortalEventSchedule.conference_id == PortalConference.id)
            .where(PortalEventSchedule.id == event_id)
            .fetchrow(as_model=EventInfoDetail)
        )
        if not item:
            raise NotFoundException(detail=f"Event info {event_id} not found")
        return item

    async def create_event_info(self, model: EventInfoCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        event_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalEventSchedule)
                .values(
                    model.model_dump(exclude_none=True),
                    id=event_id,
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Event info {model.title} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=event_id)

    async def update_event_info(self, event_id: uuid.UUID, model: EventInfoUpdate) -> None:
        """

        :param event_id:
        :param model:
        :return:
        """
        try:
            await (
                self._session.insert(PortalEventSchedule)
                .values(
                    model.model_dump(exclude_none=True),
                    id=event_id,
                )
                .on_conflict_do_update(
                    index_elements=[PortalEventSchedule.id],
                    set_={
                        "updated_at": sa.func.now(),
                        **model.model_dump()
                    },
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Event info {model.title} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    async def delete_event_info(self, event_id: uuid.UUID) -> None:
        """

        :param event_id:
        :return:
        """
        try:
            await (
                self._session.delete(PortalEventSchedule)
                .where(PortalEventSchedule.id == event_id)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
