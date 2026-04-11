"""
UserHandler
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import pytz
import sqlalchemy as sa
from redis.asyncio import Redis
from starlette import status

from portal.config import settings
from portal.exceptions.responses import ApiBaseException, NotFoundException
from portal.libs.consts.enums import Gender
from portal.libs.consts.ticket_type_codes import (
    TICKET_TYPE_CODE_INTERPRETATION_RECEIVER,
    TICKET_TYPE_CODE_SUBSTRING_CREATIVE,
    TICKET_TYPE_CODE_SUBSTRING_LEADERSHIP,
)
from portal.libs.contexts.user_context import get_user_context, UserContext
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import (
    PortalUser,
    PortalUserProfile,
    PortalThirdPartyProvider,
    PortalUserThirdPartyAuth,
    PortalUserTicket,
    PortalTicketType,
)
from portal.schemas.auth import FirebaseTokenPayload
from portal.schemas.user import SUserThirdParty, SAuthProvider, SUserDetail
from portal.serializers.v1.ticket import TicketBase
from portal.serializers.v1.user import UserUpdate, UserDetail

if TYPE_CHECKING:
    from portal.handlers.workshop import WorkshopHandler


class UserHandler:
    """UserHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        workshop_handler: "WorkshopHandler",
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._workshop_handler = workshop_handler
        # contexts
        self._user_ctx: UserContext = get_user_context()

    @distributed_trace()
    async def create_user(
        self,
        token_payload: FirebaseTokenPayload,
        provider: SAuthProvider,
    ) -> SUserThirdParty:
        """

        :param token_payload:
        :param provider:
        :return:
        """
        user_id = uuid.uuid4()
        now = datetime.now(tz=pytz.UTC)
        try:
            await (
                self._session.insert(PortalUser)
                .values(
                    id=user_id,
                    phone_number=token_payload.phone_number,
                    email=token_payload.email,
                    verified=True,
                    last_login_at=now,
                )
                .execute()
            )
            await (
                self._session.insert(PortalUserProfile)
                .values(
                    user_id=user_id,
                    is_ministry=False,
                )
                .execute()
            )
            await (
                self._session.insert(PortalUserThirdPartyAuth)
                .values(
                    user_id=user_id,
                    provider_id=provider.id,
                    provider_uid=token_payload.user_id,
                    additional_data=token_payload.model_dump_json(
                        exclude={"name", "email", "phone_number", "exp", "iat", "user_id"}
                    ),
                )
                .execute()
            )
        except Exception as e:
            raise e
        else:
            return SUserThirdParty(
                id=user_id,
                phone_number=token_payload.phone_number,
                email=token_payload.email,
                verified=True,
                is_active=True,
                is_superuser=False,
                is_admin=False,
                last_login_at=now,
                display_name=token_payload.name,
                gender=Gender.UNKNOWN,
                is_ministry=False,
                provider_id=provider.id,
                provider=provider.name,
                provider_uid=token_payload.user_id,
                additional_data=token_payload.model_dump(
                    exclude={"name", "email", "phone_number", "exp", "iat", "user_id"}
                )
            )

    @distributed_trace()
    async def get_provider_by_name(self, name: str) -> Optional[SAuthProvider]:
        """

        :param name:
        :return:
        """
        provider: Optional[SAuthProvider] = await (
            self._session.select(
                PortalThirdPartyProvider.id,
                PortalThirdPartyProvider.name,
            )
            .where(PortalThirdPartyProvider.name == name)
            .fetchrow(as_model=SAuthProvider)
        )
        return provider

    @distributed_trace()
    async def get_user_detail_by_provider_info(self, provider_uid: str, email: str = None) -> Optional[SUserThirdParty]:
        """
        Get user detail by provider id
        :param provider_uid:
        :param email:
        :return:
        """
        user: Optional[SUserThirdParty] = await (
            self._session.select(
                PortalUser.id,
                PortalUser.phone_number,
                PortalUser.email,
                PortalUser.verified,
                PortalUser.is_active,
                PortalUser.is_superuser,
                PortalUser.is_admin,
                PortalUser.last_login_at,
                PortalUserProfile.display_name,
                PortalUserProfile.gender,
                PortalUserProfile.is_ministry,
                PortalThirdPartyProvider.id.label("provider_id"),
                PortalThirdPartyProvider.name.label("provider"),
                PortalUserThirdPartyAuth.provider_uid,
                PortalUserThirdPartyAuth.additional_data
            )
            .outerjoin(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .outerjoin(PortalUserThirdPartyAuth, PortalUser.id == PortalUserThirdPartyAuth.user_id)
            .outerjoin(PortalThirdPartyProvider, PortalUserThirdPartyAuth.provider_id == PortalThirdPartyProvider.id)
            .where(email is None, lambda: PortalUserThirdPartyAuth.provider_uid == provider_uid)
            .where(email is not None, lambda: sa.or_(PortalUserThirdPartyAuth.provider_uid == provider_uid, PortalUser.email == email))
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchrow(as_model=SUserThirdParty)
        )
        if not user:
            return None
        return user

    @distributed_trace()
    async def get_user_tp_detail_by_email(self, email: str) -> Optional[SUserThirdParty]:
        """
        Get user third party detail by email
        :param email:
        :return:
        """
        user: Optional[SUserThirdParty] = await (
            self._session.select(
                PortalUser.id,
                PortalUser.phone_number,
                PortalUser.email,
                PortalUser.verified,
                PortalUser.is_active,
                PortalUser.is_superuser,
                PortalUser.is_admin,
                PortalUser.last_login_at,
                PortalUserProfile.display_name,
                PortalUserProfile.gender,
                PortalUserProfile.is_ministry,
                PortalThirdPartyProvider.id.label("provider_id"),
                PortalThirdPartyProvider.name.label("provider"),
                PortalUserThirdPartyAuth.provider_uid,
                PortalUserThirdPartyAuth.additional_data
            )
            .outerjoin(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .outerjoin(PortalUserThirdPartyAuth, PortalUser.id == PortalUserThirdPartyAuth.user_id)
            .outerjoin(PortalThirdPartyProvider, PortalUserThirdPartyAuth.provider_id == PortalThirdPartyProvider.id)
            .where(PortalUser.email == email)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchrow(as_model=SUserThirdParty)
        )
        if not user:
            return None
        return user

    @distributed_trace()
    async def ensure_portal_user_and_profile_by_email(self, email: str) -> uuid.UUID:
        """
        Ensure portal user and profile exist for the given email.
        :param email:
        :return:
        """
        existed_user_id = await (
            self._session.select(PortalUser.id)
            .where(PortalUser.email == email)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchval()
        )
        if existed_user_id:
            return existed_user_id

        user_id = uuid.uuid4()
        await (
            self._session.insert(PortalUser)
            .values(
                id=user_id,
                phone_number=None,
                email=email,
                verified=False,
            )
            .execute()
        )
        await (
            self._session.insert(PortalUserProfile)
            .values(
                user_id=user_id,
                is_ministry=False,
            )
            .execute()
        )
        return user_id

    @distributed_trace()
    async def get_user_detail_by_id(self, user_id: uuid.UUID) -> Optional[SUserDetail]:
        """

        :param user_id:
        :return:
        """
        user: Optional[SUserDetail] = await (
            self._session.select(
                PortalUser.id,
                PortalUser.phone_number,
                PortalUser.email,
                PortalUser.verified,
                PortalUser.is_active,
                PortalUser.is_superuser,
                PortalUser.is_admin,
                PortalUser.last_login_at,
                PortalUserProfile.display_name,
                PortalUserProfile.gender,
                PortalUserProfile.is_ministry
            )
            .outerjoin(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(PortalUser.id == user_id)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchrow(as_model=SUserDetail)
        )
        if not user:
            return None
        return user

    @distributed_trace()
    async def update_last_login_at(self, user_id: uuid.UUID) -> None:
        await (
            self._session.update(PortalUser)
            .values(last_login_at=datetime.now(tz=pytz.UTC))
            .where(PortalUser.id == user_id)
            .execute()
        )

    @distributed_trace()
    async def mark_user_verified(self, user_id: uuid.UUID) -> None:
        await (
            self._session.update(PortalUser)
            .values(verified=True)
            .where(PortalUser.id == user_id)
            .execute()
        )

    @distributed_trace()
    async def update_profile_display_name_if_empty(
        self,
        user_id: uuid.UUID,
        display_name: Optional[str],
    ) -> None:
        if not display_name or not display_name.strip():
            return
        await (
            self._session.update(PortalUserProfile)
            .values(display_name=display_name.strip()[:64])
            .where(PortalUserProfile.user_id == user_id)
            .where(
                sa.or_(
                    PortalUserProfile.display_name.is_(None),
                    PortalUserProfile.display_name == "",
                )
            )
            .execute()
        )

    @distributed_trace()
    async def get_user(self, user_id: uuid.UUID) -> UserDetail:
        """
        Get user detail. Ticket is the primary pass (non-INTERPRETATION_RECEIVER).
        ticket.has_interpretation_receiver / interpretation_receiver_checked_in describe the 口譯機 add-on.
        :param user_id:
        :return:
        """
        if user_id != self._user_ctx.user_id:
            raise ApiBaseException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        user: Optional[UserDetail] = await (
            self._session.select(
                PortalUser.id,
                PortalUser.phone_number,
                PortalUser.email,
                PortalUserProfile.display_name,
                PortalUserProfile.is_ministry.label("volunteer")
            )
            .join(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(PortalUser.id == user_id)
            .fetchrow(as_model=UserDetail)
        )
        if not user:
            raise NotFoundException(detail=f"User {user_id} not found")
        ir_row = await (
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
        has_interpretation_receiver = ir_row is not None
        interpretation_receiver_checked_in = (
            bool(ir_row["is_checked_in"]) if ir_row else None
        )
        ticket = await (
            self._session.select(
                PortalUserTicket.id,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalTicketType.id, sa.String),
                    sa.cast("name", sa.VARCHAR(255)), PortalTicketType.name,
                    sa.cast("code", sa.VARCHAR(32)), PortalTicketType.code,
                ).label("type"),
                PortalUserTicket.order_id,
                PortalUserTicket.is_redeemed,
                PortalUserTicket.is_checked_in,
                PortalUserTicket.checked_in_at,
                PortalUserTicket.identity,
                PortalUserTicket.belong_church
            )
            .select_from(PortalUserTicket)
            .join(PortalTicketType, PortalTicketType.id == PortalUserTicket.ticket_type_id)
            .where(PortalUserTicket.user_id == user_id)
            .where(PortalTicketType.code != TICKET_TYPE_CODE_INTERPRETATION_RECEIVER)
            .fetchrow(as_model=TicketBase)
        )
        if ticket:
            user.ticket = ticket.model_copy(
                update={
                    "has_interpretation_receiver": has_interpretation_receiver,
                    "interpretation_receiver_checked_in": (
                        interpretation_receiver_checked_in
                        if has_interpretation_receiver
                        else None
                    ),
                }
            )
            ticket_code_upper = (ticket.type.code or "").upper()
            if TICKET_TYPE_CODE_SUBSTRING_CREATIVE in ticket_code_upper:
                user.creative_session = (
                    await self._workshop_handler.get_pass_session_workshops_for_user(
                        user_id, is_creative=True, is_leadership=False
                    )
                )
            if TICKET_TYPE_CODE_SUBSTRING_LEADERSHIP in ticket_code_upper:
                user.leadership_session = (
                    await self._workshop_handler.get_pass_session_workshops_for_user(
                        user_id, is_creative=False, is_leadership=True
                    )
                )
        return user

    @distributed_trace()
    async def update_user(self, user_id: uuid.UUID, model: UserUpdate) -> None:
        """
        Update user profile
        :param user_id:
        :param model:
        :return:
        """
        if user_id != self._user_ctx.user_id:
            raise ApiBaseException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        if model.phone_number:
            await (
                self._session.update(PortalUser)
                .values(phone_number=model.phone_number)
                .where(PortalUser.id == user_id)
                .execute()
            )
        await (
            self._session.update(PortalUserProfile)
            .values(
                **model.model_dump(exclude_none=True, exclude={"phone_number"})
            )
            .where(PortalUserProfile.user_id == user_id)
            .execute()
        )

    @distributed_trace()
    async def delete_user(self, user_id: uuid.UUID) -> None:
        """

        :param user_id:
        :return:
        """
        if user_id != self._user_ctx.user_id:
            raise ApiBaseException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        await (
            self._session.update(PortalUser)
            .values(
                is_active=False,
                deleted_at=datetime.now(tz=pytz.UTC),
            )
            .where(PortalUser.id == user_id)
            .execute()
        )
