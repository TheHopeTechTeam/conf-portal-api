"""
Ticket type sync event: sync ticket types from ticket system to PortalTicketType
"""
from portal.libs.events.base import BaseEvent


class TicketTypeSyncEvent(BaseEvent):
    """
    Event to sync ticket types from the ticket system API into PortalTicketType.
    Used on app startup and when admin ticket-type list API is called with stale cache.
    """
