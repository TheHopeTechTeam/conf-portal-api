"""
Ticket type sync event handler: sync ticket types from ticket system to PortalTicketType
"""
import time

from redis.asyncio import Redis

from portal.config import settings
from portal.libs.consts.ticket_type_sync import REDIS_KEY_TICKET_TYPE_SYNC_AT
from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.events.base import EventHandler
from portal.libs.events.types import TicketTypeSyncEvent
from portal.libs.logger import logger
from portal.models import PortalTicketType
from portal.providers.thehope_ticket_provider import TheHopeTicketProvider


class TicketTypeSyncEventHandler(EventHandler):
    """
    Handler for TicketTypeSyncEvent: fetch ticket types from API and upsert into PortalTicketType.
    On success, sets Redis key for last sync time (used by list API TTL check).
    """

    def __init__(
        self,
        session: Session,
        thehope_ticket_provider: TheHopeTicketProvider,
        redis_client,
    ):
        self._session = session
        self._thehope_ticket_provider = thehope_ticket_provider
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @property
    def event_type(self) -> type[TicketTypeSyncEvent]:
        return TicketTypeSyncEvent

    @distributed_trace()
    async def handle(self, event: TicketTypeSyncEvent) -> None:
        """
        Fetch ticket types from ticket system and upsert into PortalTicketType by name.
        Then update Redis last_sync timestamp.
        """
        logger.info("Processing ticket type sync event")
        try:
            types_list = await self._thehope_ticket_provider.get_ticket_types()
        except Exception as e:
            logger.error("Failed to fetch ticket types: %s", e, exc_info=True)
            raise

        for item in types_list or []:
            name = (item.name or "").strip()
            if not name:
                continue
            await (
                self._session.insert(PortalTicketType)
                .values(id=item.id, name=name)
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={"name": name},
                )
                .execute()
            )
        if types_list:
            logger.debug("Upserted %s ticket type(s)", len(types_list))

        try:
            await self._redis.set(REDIS_KEY_TICKET_TYPE_SYNC_AT, str(time.time()))
        except Exception as e:
            logger.warning("Failed to set ticket type sync timestamp in Redis: %s", e)

        logger.info("Ticket type sync completed, types count=%s", len(types_list or []))
