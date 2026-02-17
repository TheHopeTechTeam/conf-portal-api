"""
Ticket API (user ticket check-in)
"""
from dependency_injector.wiring import inject, Provide
from fastapi import Depends, status

from portal.container import Container
from portal.handlers.ticket import TicketHandler
from portal.routers.auth_router import AuthRouter
from portal.serializers.v1.ticket import CheckInRequest, CheckInResponse

router: AuthRouter = AuthRouter(is_admin=False)


@router.post(
    path="/check-in",
    status_code=status.HTTP_200_OK,
    response_model=CheckInResponse,
    description="Check in a ticket using ticket ID from QR code. Only ministry partners can use.",
    operation_id="ticket_check_in",
)
@inject
async def check_in_ticket(
    model: CheckInRequest,
    ticket_handler: TicketHandler = Depends(Provide[Container.ticket_handler]),
) -> CheckInResponse:
    """
    Check in a ticket. Scanner sends ticket_id from QR code.
    Returns structured response for UI (success/failure, message, ticket holder info, workshop status).
    """
    return await ticket_handler.check_in_ticket(ticket_id=model.ticket_id)
