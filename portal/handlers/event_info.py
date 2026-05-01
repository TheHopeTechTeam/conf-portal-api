"""
EventInfoHandler
"""
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from redis.asyncio import Redis

from portal.config import settings
from portal.libs.consts.cache_keys import CacheExpiry, create_event_schedule_key
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.models import PortalEventSchedule
from portal.serializers.v1.event_info import EventScheduleBase, EventScheduleItem, EventScheduleList


class EventInfoHandler:
    """EventInfoHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @distributed_trace()
    async def get_event_schedule(self, conference_id: uuid.UUID) -> EventScheduleList:
        """
        Get event schedule
        :return:
        """
        cache_key = create_event_schedule_key(str(conference_id))
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                return EventScheduleList.model_validate_json(cached)
        except Exception as exc:
            logger.warning(f"get_event_schedule: failed to read cache: {exc}")
        event_schedules: Optional[list[EventScheduleBase]] = await (
            self._session.select(
                PortalEventSchedule.id,
                PortalEventSchedule.title,
                PortalEventSchedule.description,
                PortalEventSchedule.start_datetime.label("start_time"),
                PortalEventSchedule.timezone.label("time_zone"),
                PortalEventSchedule.background_color
            )
            .where(PortalEventSchedule.conference_id == conference_id)
            .order_by(PortalEventSchedule.start_datetime)
            .fetch(as_model=EventScheduleBase)
        )
        event_schedule_item_list = []
        event_schedule_map = defaultdict(list)
        for event_schedule in event_schedules:
            start_time_with_tz = event_schedule.start_time.astimezone(tz=ZoneInfo(event_schedule.time_zone))
            event_schedule.start_time = start_time_with_tz
            event_schedule_map[start_time_with_tz.date()].append(event_schedule)

        for start_time, schedules in event_schedule_map.items():  # type: (datetime, list[EventScheduleBase])
            event_schedule_item_list.append(
                EventScheduleItem(
                    date=start_time,
                    weekday=start_time.strftime("%a"),
                    schedules=schedules
                )
            )

        result = EventScheduleList(schedules=event_schedule_item_list)
        try:
            await self._redis.set(cache_key, result.model_dump_json(), ex=CacheExpiry.MINUTE * 10)
        except Exception as exc:
            logger.warning(f"get_event_schedule: failed to write cache: {exc}")
        return result
