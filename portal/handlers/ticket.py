"""
TicketHandler: sync user ticket from ticket system to PortalUserTicket.
"""
import sqlalchemy as sa
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from portal.exceptions.responses import BadRequestException, ForbiddenException, NotFoundException
from portal.libs.consts.ticket_type_codes import TICKET_TYPE_CODE_INTERPRETATION_RECEIVER
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
    ):
        self._session = session
        self._thehope_ticket_provider = thehope_ticket_provider

    @distributed_trace()
    async def sync_user_ticket(self, user_id: UUID, email: str) -> None:
        """
        Sync user tickets from ticket system to PortalUserTicket.
        Fetches all tickets by user email (including add-ons e.g. interpretation receiver) and upserts each into PortalUserTicket.
        :param user_id: Portal user id to associate with the ticket
        :param email: User email to fetch ticket from ticket system
        :return:
        """
        tickets = await self._thehope_ticket_provider.get_ticket_by_email(
            user_email=email
        )
        if not tickets:
            return

        roles = {
            "senior-pastor": "主任牧師",
            "pastor": "牧師",
            "minister": "傳道",
            "ministry-leader": "事工團隊領袖",
            "seminarian": "神學生",
            "staff": "全職同工",
            "default": "會眾",
        }
        first_ticket_user_name: str = ""
        for ticket in tickets:
            if isinstance(ticket.ticket_type, TheHopeTicketType):
                ticket_type_id = ticket.ticket_type.id
            elif isinstance(ticket.ticket_type, (UUID, str)):
                ticket_type_id = (
                    UUID(ticket.ticket_type)
                    if isinstance(ticket.ticket_type, str)
                    else ticket.ticket_type
                )
            else:
                continue
            if isinstance(ticket.order, TheHopeTicketOrder):
                order_id = ticket.order.id
            elif isinstance(ticket.order, (UUID, str)):
                order_id = (
                    UUID(ticket.order) if isinstance(ticket.order, str) else ticket.order
                )
            else:
                continue

            is_redeemed = bool(ticket.is_redeemed) if ticket.is_redeemed is not None else False
            is_checked_in = bool(ticket.is_checked_in) if ticket.is_checked_in is not None else False
            identity = (
                roles.get(ticket.user.role, "會眾")
                if ticket.user
                else "會眾"
            )
            belong_church = ticket.user.location if ticket.user else None
            if ticket.user and not first_ticket_user_name:
                first_ticket_user_name = ticket.user.name or ""

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
        if not display_name and first_ticket_user_name:
            await (
                self._session.update(PortalUserProfile)
                .values(display_name=first_ticket_user_name[:64])
                .where(PortalUserProfile.user_id == user_id)
                .execute()
            )

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

    async def _interpretation_receiver_flags_for_user(
        self, user_id: UUID
    ) -> tuple[bool, Optional[bool]]:
        """
        :return: (has_interpretation_receiver, interpretation_receiver_checked_in or None if no IR)
        """
        row = await (
            self._session.select(PortalUserTicket.is_checked_in)
            .select_from(PortalUserTicket)
            .join(
                PortalTicketType,
                PortalTicketType.id == PortalUserTicket.ticket_type_id,
            )
            .where(PortalUserTicket.user_id == user_id)
            .where(PortalTicketType.code == TICKET_TYPE_CODE_INTERPRETATION_RECEIVER)
            .fetchrow()
        )
        if not row:
            return False, None
        return True, bool(row["is_checked_in"])

    async def _interpretation_receiver_ticket_id_for_user(self, user_id: UUID) -> Optional[UUID]:
        return await (
            self._session.select(PortalUserTicket.id)
            .select_from(PortalUserTicket)
            .join(
                PortalTicketType,
                PortalTicketType.id == PortalUserTicket.ticket_type_id,
            )
            .where(PortalUserTicket.user_id == user_id)
            .where(PortalTicketType.code == TICKET_TYPE_CODE_INTERPRETATION_RECEIVER)
            .fetchval()
        )

    async def _is_interpretation_receiver_ticket(
        self, ticket_id: UUID, external_ticket
    ) -> bool:
        """True if ticket is Interpretation Receiver (DB portal_ticket_type.code or CMS meta.conf_code)."""
        code_row = await (
            self._session.select(PortalTicketType.code)
            .select_from(PortalUserTicket)
            .join(
                PortalTicketType,
                PortalTicketType.id == PortalUserTicket.ticket_type_id,
            )
            .where(PortalUserTicket.id == ticket_id)
            .fetchval()
        )
        if code_row == TICKET_TYPE_CODE_INTERPRETATION_RECEIVER:
            return True
        tt = external_ticket.ticket_type
        if isinstance(tt, TheHopeTicketType) and tt.meta:
            if tt.meta.get("conf_code") == TICKET_TYPE_CODE_INTERPRETATION_RECEIVER:
                return True
        return False

    @distributed_trace()
    async def check_in_ticket(
        self, ticket_id: UUID, interpretation_receiver: bool = False
    ) -> CheckInResponse:
        """
        Main pass check-in, or IR redeem when interpretation_receiver=True (ticket_id is main pass QR).
        """
        user_ctx = get_user_context()
        if not user_ctx or not user_ctx.user_id:
            raise ForbiddenException(detail="Authentication required")
        if not user_ctx.is_ministry:
            raise ForbiddenException(detail="Only ministry partners can perform check-in")

        if interpretation_receiver:
            return await self._check_in_interpretation_receiver_by_main_ticket_id(ticket_id)

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

    async def _check_in_interpretation_receiver_by_main_ticket_id(
        self, main_ticket_id: UUID
    ) -> CheckInResponse:
        """
        Redeem IR using main pass ticket_id: resolve holder, then check in their IR ticket.
        Responses use main_ticket_id for holder context in _build_check_in_response.
        """
        main_ticket = await self._thehope_ticket_provider.get_ticket_by_id(main_ticket_id)
        if main_ticket is None:
            return CheckInResponse(success=False, message="系統查無此票券資訊")
        if await self._is_interpretation_receiver_ticket(main_ticket_id, main_ticket):
            return await self._build_check_in_response(
                ticket_id=main_ticket_id,
                success=False,
                message="請掃描主票 QR 辦理口譯機領取",
                include_workshop_status=False,
            )
        portal_user_id = await (
            self._session.select(PortalUserTicket.user_id)
            .select_from(PortalUserTicket)
            .where(PortalUserTicket.id == main_ticket_id)
            .fetchval()
        )
        if portal_user_id is None:
            return await self._build_check_in_response(
                ticket_id=main_ticket_id,
                success=False,
                message="無法確認持有人，請稍後再試或完成票券同步",
                include_workshop_status=False,
            )
        ir_id = await self._interpretation_receiver_ticket_id_for_user(portal_user_id)
        if ir_id is None:
            return await self._build_check_in_response(
                ticket_id=main_ticket_id,
                success=False,
                message="此票卷沒有加購口譯機",
                include_workshop_status=False,
            )
        ir_ticket = await self._thehope_ticket_provider.get_ticket_by_id(ir_id)
        if ir_ticket is None:
            return await self._build_check_in_response(
                ticket_id=main_ticket_id,
                success=False,
                message="口譯機票券資料異常",
                include_workshop_status=False,
            )
        ir_checked_in = bool(ir_ticket.is_checked_in) if ir_ticket.is_checked_in is not None else False
        if ir_checked_in:
            return await self._build_check_in_response(
                ticket_id=main_ticket_id,
                success=False,
                message="此票卷已經兌換過口譯機",
                include_workshop_status=False,
            )
        await self._thehope_ticket_provider.check_in_ticket(ir_id)
        checked_in_at = datetime.now(timezone.utc)
        await (
            self._session.update(PortalUserTicket)
            .where(PortalUserTicket.id == ir_id)
            .values(is_checked_in=True, checked_in_at=checked_in_at)
            .execute()
        )
        return await self._build_check_in_response(
            ticket_id=main_ticket_id,
            success=True,
            message="兌換成功",
            include_workshop_status=False,
        )

    async def _build_check_in_response(
        self,
        ticket_id: UUID,
        success: bool,
        message: str,
        include_workshop_status: bool = True,
    ) -> CheckInResponse:
        """
        Build CheckInResponse from ticket_id and context.
        :param include_workshop_status: False for interpretation receiver redeem (skip workshop query).
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
        if not row:
            return CheckInResponse(success=success, message=message)

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

        has_ir, ir_checked_in = await self._interpretation_receiver_flags_for_user(row["id"])
        ticket_base = ticket_base.model_copy(
            update={
                "has_interpretation_receiver": has_ir,
                "interpretation_receiver_checked_in": ir_checked_in if has_ir else None,
            }
        )
        workshop_status = None
        if include_workshop_status:
            workshop_status = await self._get_workshop_registration_status(row["id"])
        return CheckInResponse(
            success=success,
            message=message,
            ticket=ticket_base,
            workshop_registration_status=workshop_status,
            email=row["email"],
            display_name=row["display_name"]
        )

