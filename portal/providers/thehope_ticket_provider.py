"""
The Hope Ticket Provider: data objectification and processing for ticket API responses.
"""
from typing import Optional
from uuid import UUID

from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.schemas.thehope_ticket import (
    TheHopeTicket,
    TheHopeTicketCheckInResponse,
    TheHopeTicketsListResponse,
    TheHopeTicketType,
    TheHopeTicketTypesResponse,
)
from portal.services.thehope_ticket import TheHopeTicketService


class TheHopeTicketProvider:
    """Provider for The Hope ticket data: objectify API responses and apply processing logic."""

    def __init__(self, thehope_ticket_service: TheHopeTicketService):
        self._service = thehope_ticket_service

    @distributed_trace()
    async def get_ticket_types(self) -> list[TheHopeTicketType]:
        """
        Get ticket types (processed list).
        :return:
        """
        raw = await self._service.get_ticket_types()
        model = TheHopeTicketTypesResponse.model_validate(raw)
        return model.docs


    @distributed_trace()
    async def get_ticket_list_by_email(self, user_email: str) -> Optional[TheHopeTicketsListResponse]:
        """
        Fetch tickets by user email, parse raw response into TheHopeTicketsListResponse.
        :param user_email:
        :return:
        """
        raw = await self._service.get_ticket_list_by_email(user_email)
        if raw is None:
            return None
        return TheHopeTicketsListResponse.model_validate(raw)

    @distributed_trace()
    async def get_ticket_by_id(self, ticket_id: UUID) -> Optional[TheHopeTicket]:
        """
        Get ticket by id from ticket system API.
        :param ticket_id:
        :return:
        """
        raw = await self._service.get_ticket_by_id(ticket_id)
        if raw is None:
            return None
        return TheHopeTicket.model_validate(raw)

    @distributed_trace()
    async def get_ticket_by_email(self, user_email: str) -> Optional[TheHopeTicket]:
        """
        Get tickets by email and return only the list of ticket objects (processed for convenience).
        :param user_email:
        :return:
        """
        response = await self.get_ticket_list_by_email(user_email)
        if response is None:
            return None
        return response.docs[0]

    @distributed_trace()
    async def check_in_ticket(self, ticket_id: UUID) -> TheHopeTicketCheckInResponse:
        """
        Check in a ticket by id via external ticket API.
        Propagates exception on failure so caller can avoid DB update.
        :param ticket_id:
        :return: Parsed check-in response with doc and message
        """
        try:
            raw = await self._service.check_in_ticket(ticket_id)
            return TheHopeTicketCheckInResponse.model_validate(raw)
        except Exception as e:
            logger.error(f"Failed to check in ticket {ticket_id}: {e}")
            raise
