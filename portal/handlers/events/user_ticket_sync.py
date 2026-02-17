"""
User ticket sync event handler: delegates to TicketHandler to sync ticket from ticket system to PortalUserTicket.
"""
from portal.handlers.ticket import TicketHandler
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.events.base import EventHandler
from portal.libs.events.types import UserTicketSyncEvent
from portal.libs.logger import logger


class UserTicketSyncEventHandler(EventHandler):
    """
    Handler for UserTicketSyncEvent: delegates to TicketHandler.sync_user_ticket.
    """

    def __init__(self, ticket_handler: TicketHandler):
        self._ticket_handler = ticket_handler

    @property
    def event_type(self) -> type[UserTicketSyncEvent]:
        return UserTicketSyncEvent

    @distributed_trace()
    async def handle(self, event: UserTicketSyncEvent) -> None:
        """
        Sync user ticket by delegating to TicketHandler.
        """
        logger.info(
            "Processing user ticket sync event: user_id=%s, email=%s",
            event.user_id,
            event.email,
        )
        await self._ticket_handler.sync_user_ticket(
            user_id=event.user_id,
            email=event.email,
        )
        logger.info("Synced ticket for user_id=%s", event.user_id)
