"""
TicketHandler: user ticket data from TheHope ticket API (no local PortalUserTicket storage).
"""
import hashlib
from datetime import datetime
from typing import Optional
from uuid import UUID

import sqlalchemy as sa

from portal.exceptions.responses import ForbiddenException
from portal.handlers.conference import ConferenceHandler
from portal.libs.consts.ticket_type_codes import TICKET_TYPE_CODE_INTERPRETATION_RECEIVER
from portal.libs.contexts.user_context import get_user_context
from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.models import (
    PortalConference,
    PortalUser,
    PortalUserProfile,
    PortalWorkshop,
    PortalWorkshopRegistration,
)
from portal.providers.thehope_ticket_provider import TheHopeTicketProvider
from portal.schemas.thehope_ticket import (
    TheHopeTicketType,
    TheHopeTicket, TheHopeTicketOrder,
)
from portal.serializers.v1.ticket import CheckInResponse, TicketBase, TicketType

ROLES = {
    "senior-pastor": "主任牧師",
    "pastor": "牧師",
    "minister": "傳道",
    "ministry-leader": "事工團隊領袖",
    "seminarian": "神學生",
    "staff": "全職同工",
    "default": "會眾",
}

class TicketHandler:
    """TicketHandler: read user tickets from TheHope API; check-in updates the external system only."""

    def __init__(
        self,
        session: Session,
        thehope_ticket_provider: TheHopeTicketProvider,
        conference_handler: ConferenceHandler,
    ):
        self._session = session
        self._thehope_ticket_provider = thehope_ticket_provider
        self._conference_handler = conference_handler

    @staticmethod
    def _registration_digits_from_ticket_id(ticket_id: UUID, year_two_digits: int) -> str:
        """
        Return exactly 12 decimal digits: 2-digit conference year + 10-digit derived serial.
        Deterministic: lowercase UUID, SHA-256, first 15 hex to int, mod 10^10 (same rule as ticketing clients).
        :param ticket_id: Ticket UUID (same string as external ticket id).
        :param year_two_digits: Conference year mod 100 (e.g. 26 for 2026).
        :return: 12-character numeric string, no separators.
        """
        serial_length = 10
        hash_hex_prefix_length = 15
        total_digits = 12
        year_mod = int(year_two_digits) % 100
        year_prefix = str(year_mod).zfill(2)
        normalized_uuid = str(ticket_id).lower()
        hash_hex = hashlib.sha256(normalized_uuid.encode("utf-8")).hexdigest()
        decimal = int(hash_hex[:hash_hex_prefix_length], 16)
        divisor = 10**serial_length
        serial = str(decimal % divisor).zfill(serial_length)
        digits = f"{year_prefix}{serial}"
        if len(digits) != total_digits:
            raise ValueError("registration id digit length invariant failed")
        return digits

    @staticmethod
    def _format_registration_number_display(twelve_digit: str) -> str:
        """
        Format 12 digits as XXX-XXXXX-XXXX for display (QR / UI).
        :param twelve_digit: 12 decimal digits from _registration_digits_from_ticket_id.
        :return: Dashed display string.
        """
        total_digits = 12
        if len(twelve_digit) != total_digits or not twelve_digit.isdigit():
            raise ValueError("twelve_digit must be 12 decimal digits")
        return f"{twelve_digit[:3]}-{twelve_digit[3:8]}-{twelve_digit[8:12]}"

    @staticmethod
    def _registration_number_from_ticket_id(ticket_id: UUID, year_two_digits: int) -> str:
        """
        Full display registration number for API responses.
        :param ticket_id: Ticket UUID.
        :param year_two_digits: Conference year mod 100.
        :return: Dashed registration number.
        """
        return TicketHandler._format_registration_number_display(
            TicketHandler._registration_digits_from_ticket_id(ticket_id, year_two_digits)
        )

    @distributed_trace()
    async def _registration_year_two_digits_from_active_conference(self) -> Optional[int]:
        """
        Year mod 100 from the active conference start_date (same source as ConferenceHandler.get_active_conference).
        :return: None when no active conference or loading it fails.
        """
        try:
            conference = await self._conference_handler.get_active_conference()
        except ValueError:
            return None
        except Exception as e:
            logger.exception(
                "_registration_year_two_digits_from_active_conference: get_active_conference failed",
                extra={"error": str(e)},
            )
            return None
        if conference.start_date is None:
            return None
        return conference.start_date.year % 100

    @distributed_trace()
    async def sync_ticket_user_name(self, user_id: UUID, email: str) -> None:
        """
        If the portal profile has no display_name, set it from the first TheHope ticket member name for this email (truncated to 64 chars).
        :param user_id: Portal user whose profile may be updated.
        :param email: Email used to list tickets in the external ticket system.
        :return: None.
        """
        try:
            tickets = await self._thehope_ticket_provider.get_ticket_by_email(
                user_email=email
            )
        except Exception as e:
            logger.exception(
                "sync_ticket_user_name: failed to fetch tickets from TheHope",
                extra={"user_id": str(user_id), "holder_email": email, "error": str(e)},
            )
            return
        if not tickets:
            logger.info(
                "sync_ticket_user_name: no tickets for email, skip profile update",
                extra={"user_id": str(user_id), "holder_email": email},
            )
            return

        first_ticket_user_name: str = ""
        for ticket in tickets:
            if ticket.user and not first_ticket_user_name:
                first_ticket_user_name = ticket.user.name or ""

        try:
            display_name = await (
                self._session.select(PortalUserProfile.display_name)
                .select_from(PortalUserProfile)
                .where(PortalUserProfile.user_id == user_id)
                .fetchval()
            )
        except Exception as e:
            logger.exception(
                "sync_ticket_user_name: failed to read portal profile display_name",
                extra={"user_id": str(user_id), "holder_email": email, "error": str(e)},
            )
            return
        if not display_name and first_ticket_user_name:
            try:
                await (
                    self._session.update(PortalUserProfile)
                    .values(display_name=first_ticket_user_name[:64])
                    .where(PortalUserProfile.user_id == user_id)
                    .execute()
                )
            except Exception as e:
                logger.exception(
                    "sync_ticket_user_name: failed to update portal profile display_name",
                    extra={
                        "user_id": str(user_id),
                        "holder_email": email,
                        "source_name_len": len(first_ticket_user_name),
                        "error": str(e),
                    },
                )

    async def get_user_ticket_by_email(
        self,
        email: str,
        *,
        registration_year_two_digits: Optional[int] = None,
    ) -> Optional[TicketBase]:
        """
        Build the portal-facing primary ticket summary from TheHope tickets for the given email.
        Requires at least one non-interpretation-receiver ticket that is redeemed and consented.
        Also derives interpretation receiver (口譯機) flags from the external ticket list.
        :param email: Ticket holder email as stored in the ticket system.
        :param registration_year_two_digits: Optional two-digit conference year for registration_number; when None, derived from ConferenceHandler.get_active_conference().start_date.
        :return: TicketBase when a valid redeemed primary pass exists; None if no tickets, not redeemed, parse error, or consent missing.
        """
        try:
            tickets: list[TheHopeTicket] = await self._thehope_ticket_provider.get_ticket_by_email(user_email=email)
        except Exception as e:
            logger.exception(
                "get_user_ticket_by_email: TheHope list-by-email failed",
                extra={"holder_email": email, "error": str(e)},
            )
            return None
        if not tickets:
            logger.info(
                "get_user_ticket_by_email: empty ticket list",
                extra={"holder_email": email},
            )
            return None
        try:
            is_actual_redeemed = False  # user must have is_redeemed and consentedAt
            ticket_base_data: dict = {
                "has_interpretation_receiver": False,
                "interpretation_receiver_checked_in": False,
            }
            for ticket in tickets:
                if ticket.user.consented_at is None:
                    break
                meta = ticket.ticket_type.meta or {}
                if meta.get("conf_code") == TICKET_TYPE_CODE_INTERPRETATION_RECEIVER:
                    ticket_base_data["has_interpretation_receiver"] = True
                    if ticket.is_checked_in and ticket.user.consented_at is not None:
                        ticket_base_data["interpretation_receiver_checked_in"] = True
                    continue
                else:
                    ticket_base_data["id"] = ticket.id
                    order_id: Optional[UUID] = None
                    if isinstance(ticket.order, TheHopeTicketOrder):
                        order_id = ticket.order.id
                    elif isinstance(ticket.order, UUID):
                        order_id = ticket.order
                    ticket_base_data["order_id"] = order_id
                    ticket_base_data["is_checked_in"] = ticket.is_checked_in
                    ticket_base_data["is_redeemed"] = ticket.is_redeemed
                    ticket_base_data["identity"] = ROLES.get(ticket.user.role, "會眾") if ticket.user.role else "會眾"
                    ticket_base_data["belong_church"] = ticket.user.location
                    if ticket.is_redeemed and ticket.user.consented_at is not None:
                        is_actual_redeemed = True

                    ticket_type_code = meta.get("conf_code")
                    if ticket_type_code:
                        ticket_base_data["type"] = {
                            "id": ticket.ticket_type.id,
                            "name": ticket.ticket_type.name,
                            "code": ticket_type_code,
                        }
                    else:
                        ticket_base_data["type"] = None

            if not is_actual_redeemed:
                logger.warning(
                    "get_user_ticket_by_email: no redeemed primary pass after scan",
                    extra={
                        "holder_email": email,
                        "ticket_doc_count": len(tickets),
                        "first_ticket_id": str(tickets[0].id) if tickets else None,
                    },
                )
                return None
            ticket_uuid = ticket_base_data.get("id")
            if ticket_uuid is not None:
                year_two_digits = registration_year_two_digits
                if year_two_digits is None:
                    year_two_digits = await self._registration_year_two_digits_from_active_conference()
                if year_two_digits is not None:
                    ticket_base_data["registration_number"] = self._registration_number_from_ticket_id(
                        ticket_uuid,
                        year_two_digits,
                    )
            return TicketBase.model_validate(ticket_base_data)
        except Exception as e:
            logger.exception(
                "get_user_ticket_by_email: parse or validate failed",
                extra={
                    "holder_email": email,
                    "ticket_doc_count": len(tickets),
                    "error": str(e),
                },
            )
            return None

    def _time_ranges_overlap(
        self,
        a_start: datetime,
        a_end: datetime,
        b_start: datetime,
        b_end: datetime,
    ) -> bool:
        """
        Return whether two half-open style datetime ranges overlap (used for workshop timeslot coverage).
        :param a_start: Start of range A.
        :param a_end: End of range A.
        :param b_start: Start of range B.
        :param b_end: End of range B.
        :return: True if the ranges overlap; False otherwise.
        """
        return (
            (a_start >= b_start and a_start < b_end)
            or (a_end > b_start and a_end <= b_end)
            or (a_start <= b_start and a_end >= b_end)
        )

    async def _get_workshop_registration_status(self, user_id: UUID) -> str:
        """
        Summarize whether the portal user has registered a workshop overlapping every active-conference workshop timeslot.
        :param user_id: Portal user id for workshop registration rows.
        :return: "已全部報名" if every timeslot is covered by a registration; otherwise "尚未報名工作坊" (including when there are no workshops).
        """
        try:
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
        except Exception as e:
            logger.exception(
                "_get_workshop_registration_status: query failed, defaulting to not fully registered",
                extra={"portal_user_id": str(user_id), "error": str(e)},
            )
            return "尚未報名工作坊"

    def _ticket_base_from_thehope_ticket(
        self,
        ticket: TheHopeTicket,
        registration_year_two_digits: Optional[int],
    ) -> Optional[TicketBase]:
        """
        Map one TheHope ticket document to TicketBase (e.g. check-in UI when get_user_ticket_by_email returns None).
        Interpretation receiver addon fields are defaulted; callers may overwrite them after merging email-wide data.
        :param ticket: Parsed ticket from TheHope API (typically the QR-scanned ticket).
        :param registration_year_two_digits: Two-digit year for registration_number; None skips the field.
        :return: TicketBase built from that ticket only, or None if mapping fails (error is logged).
        """
        try:
            tt = ticket.ticket_type
            meta = tt.meta or {}
            code = meta.get("conf_code")
            registration_number = None
            if registration_year_two_digits is not None:
                registration_number = self._registration_number_from_ticket_id(
                    ticket.id,
                    registration_year_two_digits,
                )
            if not code:
                return None
            return TicketBase(
                id=ticket.id,
                registration_number=registration_number,
                order_id=ticket.order,
                is_checked_in=bool(ticket.is_checked_in) if ticket.is_checked_in is not None else False,
                is_redeemed=bool(ticket.is_redeemed) if ticket.is_redeemed is not None else False,
                identity=ROLES.get(ticket.user.role, "會眾") if ticket.user.role else "會眾",
                belong_church=ticket.user.location,
                type=TicketType(
                    id=tt.id,
                    name=tt.name,
                    code=code,
                ),
                has_interpretation_receiver=False,
                interpretation_receiver_checked_in=None,
            )
        except Exception as e:
            logger.exception(
                "_ticket_base_from_thehope_ticket: failed to map external ticket to TicketBase",
                extra={
                    "ticket_id": str(ticket.id) if getattr(ticket, "id", None) else None,
                    "order_id": str(ticket.order) if getattr(ticket, "order", None) else None,
                    "error": str(e),
                },
            )
            return None

    async def _interpretation_receiver_flags_from_email(
        self, email: str
    ) -> tuple[bool, Optional[bool]]:
        """
        Load all tickets for the email from TheHope and read interpretation receiver (口譯機) state from API data only.
        :param email: Ticket holder email in the ticket system.
        :return: Tuple of (whether an IR ticket exists, IR checked-in flag or None when no IR ticket).
        """
        try:
            tickets = await self._thehope_ticket_provider.get_ticket_by_email(user_email=email)
        except Exception as e:
            logger.exception(
                "_interpretation_receiver_flags_from_email: TheHope list-by-email failed",
                extra={"holder_email": email, "error": str(e)},
            )
            return False, None
        try:
            for ticket in tickets:
                meta = ticket.ticket_type.meta or {}
                if meta.get("conf_code") != TICKET_TYPE_CODE_INTERPRETATION_RECEIVER:
                    continue
                return True, bool(ticket.is_checked_in) if ticket.is_checked_in is not None else False
            return False, None
        except Exception as e:
            logger.exception(
                "_interpretation_receiver_flags_from_email: failed while scanning tickets",
                extra={"holder_email": email, "ticket_doc_count": len(tickets), "error": str(e)},
            )
            return False, None

    async def _interpretation_receiver_ticket_id_for_email(self, email: str) -> Optional[UUID]:
        """
        Find the external ticket id for the interpretation receiver (口譯機) add-on for this holder email.
        :param email: Ticket holder email in the ticket system.
        :return: IR ticket UUID if present; None if no IR ticket type is found for that email.
        """
        try:
            tickets = await self._thehope_ticket_provider.get_ticket_by_email(user_email=email)
        except Exception as e:
            logger.exception(
                "_interpretation_receiver_ticket_id_for_email: TheHope list-by-email failed",
                extra={"holder_email": email, "error": str(e)},
            )
            return None
        try:
            for ticket in tickets:
                meta = ticket.ticket_type.meta or {}
                if meta.get("conf_code") == TICKET_TYPE_CODE_INTERPRETATION_RECEIVER:
                    return ticket.id
            return None
        except Exception as e:
            logger.exception(
                "_interpretation_receiver_ticket_id_for_email: failed while scanning tickets",
                extra={"holder_email": email, "ticket_doc_count": len(tickets), "error": str(e)},
            )
            return None

    def _is_interpretation_receiver_ticket(self, external_ticket: TheHopeTicket) -> bool:
        """
        Detect whether a scanned ticket is the interpretation receiver (口譯機) product using ticket type meta.
        :param external_ticket: Ticket document from TheHope API.
        :return: True if ticket type meta.conf_code marks this as interpretation receiver; False otherwise.
        """
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
        Ministry check-in: either check in the main conference ticket or redeem the IR add-on using the main pass QR.
        State is written only to the external ticket API; no local user-ticket rows are updated.
        :param ticket_id: Ticket UUID from QR (main pass in both flows).
        :param interpretation_receiver: If True, redeem IR for the holder of this main pass; if False, main pass check-in.
        :return: CheckInResponse with success flag, localized message, and optional ticket holder context.
        """
        user_ctx = get_user_context()
        if not user_ctx or not user_ctx.user_id:
            raise ForbiddenException(detail="Authentication required")
        if not user_ctx.is_ministry:
            raise ForbiddenException(detail="Only ministry partners can perform check-in")

        operator_user_id = str(user_ctx.user_id)
        if interpretation_receiver:
            logger.info(
                "check_in_ticket: IR redeem flow",
                extra={
                    "main_ticket_id": str(ticket_id),
                    "operator_user_id": operator_user_id,
                },
            )
            return await self._check_in_interpretation_receiver_by_main_ticket_id(ticket_id)

        try:
            ticket = await self._thehope_ticket_provider.get_ticket_by_id(ticket_id)
        except Exception as e:
            logger.exception(
                "check_in_ticket: get_ticket_by_id failed",
                extra={"ticket_id": str(ticket_id), "operator_user_id": operator_user_id, "error": str(e)},
            )
            return CheckInResponse(success=False, message="系統查無此票券資訊")

        if ticket is None:
            logger.warning(
                "check_in_ticket: ticket not found in TheHope",
                extra={"ticket_id": str(ticket_id), "operator_user_id": operator_user_id},
            )
            return CheckInResponse(success=False, message="系統查無此票券資訊")

        is_redeemed = bool(ticket.is_redeemed) if ticket.is_redeemed is not None else False
        is_checked_in = bool(ticket.is_checked_in) if ticket.is_checked_in is not None else False

        if not is_redeemed:
            logger.info(
                "check_in_ticket: rejected, ticket not redeemed",
                extra={
                    "ticket_id": str(ticket_id),
                    "operator_user_id": operator_user_id,
                    "is_redeemed": is_redeemed,
                    "holder_email": ticket.user.email if ticket.user else None,
                },
            )
            return await self._build_check_in_response(
                ticket=ticket,
                success=False,
                message="此票卷尚未取票",
            )
        if is_checked_in:
            logger.info(
                "check_in_ticket: rejected, already checked in",
                extra={"ticket_id": str(ticket_id), "operator_user_id": operator_user_id},
            )
            return await self._build_check_in_response(
                ticket=ticket,
                success=False,
                message="此票券已完成報到",
            )

        try:
            checked_in_result = await self._thehope_ticket_provider.check_in_ticket(ticket_id)
        except Exception as e:
            logger.exception(
                "check_in_ticket: external check_in_ticket API failed",
                extra={"ticket_id": str(ticket_id), "operator_user_id": operator_user_id, "error": str(e)},
            )
            return await self._build_check_in_response(
                ticket=ticket,
                success=False,
                message="報到失敗，請稍後再試",
            )
        logger.info(
            "check_in_ticket: main pass check-in succeeded",
            extra={"ticket_id": str(ticket_id), "operator_user_id": operator_user_id},
        )
        return await self._build_check_in_response(
            ticket=checked_in_result.doc,
            success=True,
            message="報到成功",
        )

    async def _check_in_interpretation_receiver_by_main_ticket_id(
        self, main_ticket_id: UUID
    ) -> CheckInResponse:
        """
        Redeem the interpretation receiver (口譯機) ticket for the holder identified by the main pass QR ticket id.
        Resolves holder email from the main ticket, finds the IR ticket id via TheHope list-by-email, then check-in IR in the external API.
        :param main_ticket_id: Main pass ticket UUID scanned from QR (not the IR ticket id).
        :return: CheckInResponse; holder-facing payload is still built from main_ticket_id for display consistency.
        """
        try:
            main_ticket = await self._thehope_ticket_provider.get_ticket_by_id(main_ticket_id)
        except Exception as e:
            logger.exception(
                "_check_in_interpretation_receiver_by_main_ticket_id: get_ticket_by_id failed",
                extra={"main_ticket_id": str(main_ticket_id), "error": str(e)},
            )
            return CheckInResponse(success=False, message="系統查無此票券資訊")
        if main_ticket is None:
            logger.warning(
                "_check_in_interpretation_receiver_by_main_ticket_id: main ticket missing",
                extra={"main_ticket_id": str(main_ticket_id)},
            )
            return CheckInResponse(success=False, message="系統查無此票券資訊")
        if self._is_interpretation_receiver_ticket(main_ticket):
            return await self._build_check_in_response(
                ticket=main_ticket,
                success=False,
                message="請掃描主票 QR 辦理口譯機領取",
                include_workshop_status=False,
            )
        member_email = main_ticket.user.email if main_ticket.user else None
        if not member_email:
            return await self._build_check_in_response(
                ticket=main_ticket,
                success=False,
                message="無法確認持有人，票務系統缺少報名者電子郵件",
                include_workshop_status=False,
            )
        ir_id = await self._interpretation_receiver_ticket_id_for_email(member_email)
        if ir_id is None:
            logger.info(
                "_check_in_interpretation_receiver_by_main_ticket_id: no IR ticket for holder",
                extra={"main_ticket_id": str(main_ticket_id), "holder_email": member_email},
            )
            return await self._build_check_in_response(
                ticket=main_ticket,
                success=False,
                message="此票卷沒有加購口譯機",
                include_workshop_status=False,
            )
        try:
            ir_ticket = await self._thehope_ticket_provider.get_ticket_by_id(ir_id)
        except Exception as e:
            logger.exception(
                "_check_in_interpretation_receiver_by_main_ticket_id: get IR ticket failed",
                extra={"main_ticket_id": str(main_ticket_id), "ir_ticket_id": str(ir_id), "error": str(e)},
            )
            return await self._build_check_in_response(
                ticket=main_ticket,
                success=False,
                message="口譯機票券資料異常",
                include_workshop_status=False,
            )
        if ir_ticket is None:
            return await self._build_check_in_response(
                ticket=main_ticket,
                success=False,
                message="口譯機票券資料異常",
                include_workshop_status=False,
            )
        ir_checked_in = bool(ir_ticket.is_checked_in) if ir_ticket.is_checked_in is not None else False
        if ir_checked_in:
            logger.info(
                "_check_in_interpretation_receiver_by_main_ticket_id: IR already checked in",
                extra={"main_ticket_id": str(main_ticket_id), "ir_ticket_id": str(ir_id)},
            )
            return await self._build_check_in_response(
                ticket=main_ticket,
                success=False,
                message="此票卷已經兌換過口譯機",
                include_workshop_status=False,
            )
        try:
            await self._thehope_ticket_provider.check_in_ticket(ir_id)
        except Exception as e:
            logger.exception(
                "_check_in_interpretation_receiver_by_main_ticket_id: external IR check-in failed",
                extra={"main_ticket_id": str(main_ticket_id), "ir_ticket_id": str(ir_id), "error": str(e)},
            )
            return await self._build_check_in_response(
                ticket=main_ticket,
                success=False,
                message="兌換失敗，請稍後再試",
                include_workshop_status=False,
            )
        logger.info(
            "_check_in_interpretation_receiver_by_main_ticket_id: IR redeem succeeded",
            extra={"main_ticket_id": str(main_ticket_id), "ir_ticket_id": str(ir_id)},
        )
        return await self._build_check_in_response(
            ticket=main_ticket,
            success=True,
            message="兌換成功",
            include_workshop_status=False,
        )

    async def _build_check_in_response(
        self,
        ticket: TheHopeTicket,
        success: bool,
        message: str,
        include_workshop_status: bool = True,
    ) -> CheckInResponse:
        """
        Assemble check-in API payload: ticket snapshot from TheHope (already loaded by caller), portal profile when linked, and workshop summary.
        Ticket fields come from get_user_ticket_by_email when eligible, otherwise from the provided ticket object.
        :param ticket: Ticket from TheHope API; caller must ensure ticket data is already loaded.
        :param success: Whether the check-in or IR redeem operation succeeded.
        :param message: User-facing status text for the client.
        :param include_workshop_status: If True and a portal user exists for the holder email, attach workshop registration summary.
        :return: CheckInResponse with email, display name, optional ticket, and optional workshop_registration_status.
        """
        ticket_id = ticket.id
        if not ticket.user:
            logger.warning(
                "_build_check_in_response: missing ticket or user on external doc",
                extra={"ticket_id": str(ticket_id), "success": success},
            )
            return CheckInResponse(success=success, message=message)

        member_email = ticket.user.email
        if not member_email:
            logger.warning(
                "_build_check_in_response: external ticket has no member email",
                extra={"ticket_id": str(ticket_id), "success": success},
            )
            return CheckInResponse(success=success, message=message)

        try:
            row = await (
                self._session.select(
                    PortalUser.id,
                    PortalUser.email,
                    PortalUserProfile.display_name,
                )
                .select_from(PortalUser)
                .outerjoin(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
                .where(PortalUser.email == member_email)
                .where(PortalUser.is_deleted == sa.false())
                .where(PortalUser.is_active == sa.true())
                .fetchrow()
            )
        except Exception as e:
            logger.exception(
                "_build_check_in_response: portal user lookup failed",
                extra={"ticket_id": str(ticket_id), "holder_email": member_email, "error": str(e)},
            )
            row = None

        email_out = row["email"] if row else member_email
        display_name_out = row["display_name"] if row else (ticket.user.name or None)

        try:
            registration_year = await self._registration_year_two_digits_from_active_conference()
            ticket_base = await self.get_user_ticket_by_email(
                member_email,
                registration_year_two_digits=registration_year,
            )
            if not ticket_base:
                ticket_base = self._ticket_base_from_thehope_ticket(
                    ticket,
                    registration_year_two_digits=registration_year,
                )
            if not ticket_base:
                logger.warning(
                    "_build_check_in_response: no TicketBase after email and single-ticket mapping",
                    extra={"ticket_id": str(ticket_id), "holder_email": member_email},
                )
                raise ValueError("no TicketBase after email and single-ticket mapping")

            has_ir, ir_checked_in = await self._interpretation_receiver_flags_from_email(member_email)
            if ticket_base:
                ticket_base = ticket_base.model_copy(
                    update={
                        "has_interpretation_receiver": has_ir,
                        "interpretation_receiver_checked_in": ir_checked_in if has_ir else None,
                    }
                )

            workshop_status = None
            if include_workshop_status and row:
                workshop_status = await self._get_workshop_registration_status(row["id"])
            return CheckInResponse(
                success=success,
                message=message,
                ticket=ticket_base,
                workshop_registration_status=workshop_status,
                email=email_out,
                display_name=display_name_out,
            )
        except Exception as e:
            logger.exception(
                "_build_check_in_response: failed to assemble payload",
                extra={
                    "ticket_id": str(ticket_id),
                    "holder_email": member_email,
                    "success": success,
                    "error": str(e),
                },
            )
            return CheckInResponse(
                success=success,
                message=message,
                email=email_out,
                display_name=display_name_out,
            )

