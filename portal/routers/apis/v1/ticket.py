"""
Ticket API (user ticket check-in)
"""
import uuid

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, status

from portal.container import Container
from portal.handlers.ticket import TicketHandler
from portal.routers.auth_router import AuthRouter
from portal.serializers.v1.ticket import CheckInTokenRequest, CheckInTokenResponse, CheckInResponse

router: AuthRouter = AuthRouter(is_admin=False)


@router.get(
    path="/{ticket_id}/check-in-token",
    status_code=status.HTTP_200_OK,
    response_model=CheckInTokenResponse,
    description="Get one-time check-in token for QR code. User must own the ticket.",
    operation_id="ticket_check_in_token",
)
@inject
async def create_check_in_token(
    ticket_id: uuid.UUID,
    ticket_handler: TicketHandler = Depends(Provide[Container.ticket_handler]),
) -> CheckInTokenResponse:
    """
    Create a one-time check-in token for QR code. Token expires in 5 minutes and is single-use.
    """
    token, expires_at = await ticket_handler.create_check_in_token(ticket_id=ticket_id)
    return CheckInTokenResponse(token=token, expires_at=expires_at)


@router.post(
    path="/check-in",
    status_code=status.HTTP_200_OK,
    response_model=CheckInResponse,
    description="Check in a ticket using one-time token from QR code. Only ministry partners can use.",
    operation_id="ticket_check_in",
)
@inject
async def check_in_ticket(
    model: CheckInTokenRequest,
    ticket_handler: TicketHandler = Depends(Provide[Container.ticket_handler]),
) -> CheckInResponse:
    """
    Check in a ticket. Scanner sends token from QR code. Token is validated and consumed (single-use).
    Returns structured response for UI (success/failure, message, ticket holder info, workshop status).
    """
    return await ticket_handler.check_in_ticket(token=model.token)
