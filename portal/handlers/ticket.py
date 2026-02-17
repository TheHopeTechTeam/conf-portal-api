"""
TicketHandler: sync user ticket from ticket system to PortalUserTicket.
"""
import sqlalchemy as sa
from datetime import datetime, timezone
from uuid import UUID

from portal.exceptions.responses import BadRequestException, ForbiddenException, NotFoundException
from portal.libs.contexts.user_context import get_user_context
from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import (
    PortalConference,
    PortalUser,
    PortalUserProfile,
    PortalUserTicket,
    PortalTicketType,
    PortalWorkshop,
    PortalWorkshopRegistration,
)
from portal.providers.check_in_token_provider import CheckInTokenProvider
from portal.providers.thehope_ticket_provider import TheHopeTicketProvider
from portal.schemas.thehope_ticket import (
    TheHopeTicketMember,
    TheHopeTicketOrder,
    TheHopeTicketType,
)
from portal.serializers.v1.ticket import CheckInResponse, TicketBase


class TicketHandler:
    """TicketHandler: sync user ticket (non-admin)."""

    def __init__(
        self,
        session: Session,
        thehope_ticket_provider: TheHopeTicketProvider,
        check_in_token_provider: CheckInTokenProvider,
    ):
        self._session = session
        self._thehope_ticket_provider = thehope_ticket_provider
        self._check_in_token_provider = check_in_token_provider

    @distributed_trace()
    async def sync_user_ticket(self, user_id: UUID, email: str) -> None:
        """
        Sync user ticket from ticket system to PortalUserTicket.
        Fetches ticket by user email and upserts into PortalUserTicket.
        :param user_id: Portal user id to associate with the ticket
        :param email: User email to fetch ticket from ticket system
        :return:
        """
        ticket = await self._thehope_ticket_provider.get_ticket_by_email(
            user_email=email
        )
        if ticket is None:
            return

        if isinstance(ticket.ticket_type, TheHopeTicketType):
            ticket_type_id = ticket.ticket_type.id
        elif isinstance(ticket.ticket_type, (UUID, str)):
            ticket_type_id = (
                UUID(ticket.ticket_type)
                if isinstance(ticket.ticket_type, str)
                else ticket.ticket_type
            )
        else:
            return
        if isinstance(ticket.order, TheHopeTicketOrder):
            order_id = ticket.order.id
        elif isinstance(ticket.order, (UUID, str)):
            order_id = (
                UUID(ticket.order) if isinstance(ticket.order, str) else ticket.order
            )
        else:
            return

        is_redeemed = bool(ticket.is_redeemed) if ticket.is_redeemed is not None else False
        is_checked_in = bool(ticket.is_checked_in) if ticket.is_checked_in is not None else False
        roles = {
            "senior-pastor": "主任牧師",
            "pastor": "牧師",
            "minister": "傳道",
            "ministry-leader": "事工團隊領袖",
            "seminarian": "神學生",
            "staff": "全職同工",
            "default": "會眾",
        }
        identity = roles.get(ticket.user.role, "會眾")
        belong_church = ticket.user.location

        data = {
            "id": ticket.id,
            "ticket_type_id": ticket_type_id,
            "order_id": order_id,
            "user_id": user_id,
            "is_redeemed": is_redeemed,
            "is_checked_in": is_checked_in,
            "checked_in_at": None,
            "identity": identity,
            "belong_church": belong_church,
        }
        await (
            self._session.insert(PortalUserTicket)
            .values(data)
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "ticket_type_id": ticket_type_id,
                    "order_id": order_id,
                    "user_id": user_id,
                    "is_redeemed": is_redeemed,
                    "is_checked_in": is_checked_in,
                    "checked_in_at": None,
                    "identity": identity,
                    "belong_church": belong_church,
                },
            )
            .execute()
        )
        display_name = await (
            self._session.select(PortalUserProfile.display_name)
            .select_from(PortalUserProfile)
            .where(PortalUserProfile.user_id == user_id)
            .fetchval()
        )
        name = ticket.user.name or ""
        if not display_name:
            await (
                self._session.update(PortalUserProfile)
                .values(display_name=name[:64])
                .where(PortalUserProfile.user_id == user_id)
                .execute()
            )

    @distributed_trace()
    async def create_check_in_token(self, ticket_id: UUID) -> tuple[str, datetime]:
        """
        Create a one-time check-in token for QR code. User must own the ticket.
        :param ticket_id: PortalUserTicket id
        :return: (token, expires_at)
        """
        user_ctx = get_user_context()
        if not user_ctx or not user_ctx.user_id:
            raise ForbiddenException(detail="Authentication required")

        user_id = await (
            self._session.select(PortalUserTicket.user_id)
            .where(PortalUserTicket.id == ticket_id)
            .fetchval()
        )
        if not user_id:
            raise NotFoundException(detail="Ticket not found")
        if user_id != user_ctx.user_id:
            raise ForbiddenException(detail="Ticket does not belong to user")

        return self._check_in_token_provider.create_token(ticket_id)

    def _time_ranges_overlap(
        self,
        a_start: datetime,
        a_end: datetime,
        b_start: datetime,
        b_end: datetime,
    ) -> bool:
        """Check if two time ranges overlap."""
        return (
            (a_start >= b_start and a_start < b_end)
            or (a_end > b_start and a_end <= b_end)
            or (a_start <= b_start and a_end >= b_end)
        )

    async def _get_workshop_registration_status(self, user_id: UUID) -> str:
        """
        Get workshop registration status for user: 已全部報名 or 尚未報名工作坊.
        Each timeslot allows only one workshop registration. User has 已全部報名 if
        for every workshop timeslot in the active conference, the user has registered
        a workshop that overlaps that timeslot.
        """
        workshops = await (
            self._session.select(
                PortalWorkshop.id,
                PortalWorkshop.start_datetime,
                PortalWorkshop.end_datetime,
            )
            .select_from(PortalWorkshop)
            .join(PortalConference, PortalWorkshop.conference_id == PortalConference.id)
            .where(PortalWorkshop.is_deleted == sa.false())
            .where(PortalConference.is_active == sa.true())
            .fetch()
        )
        if not workshops:
            return "已全部報名"

        registrations = await (
            self._session.select(
                PortalWorkshop.start_datetime,
                PortalWorkshop.end_datetime,
            )
            .select_from(PortalWorkshopRegistration)
            .join(PortalWorkshop, PortalWorkshopRegistration.workshop_id == PortalWorkshop.id)
            .join(PortalConference, PortalWorkshop.conference_id == PortalConference.id)
            .where(PortalWorkshopRegistration.user_id == user_id)
            .where(PortalWorkshopRegistration.unregistered_at.is_(None))
            .where(PortalWorkshop.is_deleted == sa.false())
            .where(PortalConference.is_active == sa.true())
            .fetch()
        )

        for ws in workshops:
            ws_start = ws["start_datetime"]
            ws_end = ws["end_datetime"]
            has_overlap = any(
                self._time_ranges_overlap(
                    reg["start_datetime"], reg["end_datetime"], ws_start, ws_end
                )
                for reg in registrations
            )
            if not has_overlap:
                return "尚未報名工作坊"
        return "已全部報名"

    @distributed_trace()
    async def check_in_ticket(self, token: str) -> CheckInResponse:
        """
        Check in a ticket using one-time token. Only ministry users may use.
        :param token:
        :return:
        """
        user_ctx = get_user_context()
        if not user_ctx or not user_ctx.user_id:
            raise ForbiddenException(detail="Authentication required")
        if not user_ctx.is_ministry:
            raise ForbiddenException(detail="Only ministry partners can perform check-in")

        ticket_id, already_used = await self._check_in_token_provider.verify_and_consume_token(token)
        if ticket_id is None and not already_used:
            return CheckInResponse(success=False, message="系統查無此票券資訊")
        if already_used and ticket_id:
            return await self._build_check_in_response(
                ticket_id=ticket_id,
                success=False,
                message="此票券已完成報到"
            )

        ticket = await self._thehope_ticket_provider.get_ticket_by_id(ticket_id)
        if ticket is None:
            return CheckInResponse(success=False, message="系統查無此票券資訊")

        is_redeemed = bool(ticket.is_redeemed) if ticket.is_redeemed is not None else False
        is_checked_in = bool(ticket.is_checked_in) if ticket.is_checked_in is not None else False

        if not is_redeemed:
            return await self._build_check_in_response(
                ticket_id=ticket_id,
                success=False,
                message="此票卷尚未取票"
            )
        if is_checked_in:
            return await self._build_check_in_response(
                ticket_id=ticket_id,
                success=False,
                message="此票券已完成報到"
            )

        await self._thehope_ticket_provider.check_in_ticket(ticket_id)
        checked_in_at = datetime.now(timezone.utc)
        await (
            self._session.update(PortalUserTicket)
            .where(PortalUserTicket.id == ticket_id)
            .values(is_checked_in=True, checked_in_at=checked_in_at)
            .execute()
        )
        return await self._build_check_in_response(
            ticket_id=ticket_id,
            success=True,
            message="報到成功"
        )

    async def _build_check_in_response(
        self,
        ticket_id: UUID,
        success: bool,
        message: str
    ) -> CheckInResponse:
        """
        Build CheckInResponse from ticket_id and context.
        :param ticket_id:
        :param success:
        :param message:
        :return:
        """
        row = await (
            self._session.select(
                PortalUser.id,
                PortalUser.email,
                PortalUserProfile.display_name,
            )
            .select_from(PortalUserTicket)
            .join(PortalUser, PortalUserTicket.user_id == PortalUser.id)
            .join(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(PortalUserTicket.id == ticket_id)
            .fetchrow()
        )

        ticket_base = await (
            self._session.select(
                PortalUserTicket.id,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalTicketType.id, sa.String),
                    sa.cast("name", sa.VARCHAR(255)), PortalTicketType.name,
                ).label("type"),
                PortalUserTicket.order_id,
                PortalUserTicket.is_redeemed,
                PortalUserTicket.is_checked_in,
                PortalUserTicket.checked_in_at,
                PortalUserTicket.identity,
                PortalUserTicket.belong_church,
            )
            .select_from(PortalUserTicket)
            .join(PortalTicketType, PortalUserTicket.ticket_type_id == PortalTicketType.id)
            .where(PortalUserTicket.id == ticket_id)
            .fetchrow(as_model=TicketBase)
        )
        if not ticket_base:
            return CheckInResponse(
                success=success,
                message=message,
                email=row["email"],
                display_name=row["display_name"],
            )

        workshop_status = await self._get_workshop_registration_status(row["id"])
        return CheckInResponse(
            success=success,
            message=message,
            ticket=ticket_base,
            workshop_registration_status=workshop_status,
            email=row["email"],
            display_name=row["display_name"]
        )

