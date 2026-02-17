"""
User ticket sync event: sync user ticket from ticket system to PortalUserTicket
"""
from uuid import UUID

from portal.libs.events.base import BaseEvent


class UserTicketSyncEvent(BaseEvent):
    """
    Event to sync a user's ticket from the ticket system into PortalUserTicket.
    Payload: user_id and email for fetching ticket and writing to portal DB.
    """
    user_id: UUID
    email: str
