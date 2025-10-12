"""
UserHandler
"""
import uuid
from datetime import datetime
from typing import Optional

import pytz
from fastapi.security.utils import get_authorization_scheme_param
from redis.asyncio import Redis
from starlette import status

from portal.config import settings
from portal.exceptions.responses import ApiBaseException, NotFoundException
from portal.handlers.auth import AuthHandler
from portal.handlers.fcm_device import FCMDeviceHandler
from portal.libs.consts.enums import AuthProvider
from portal.libs.contexts.api_context import get_api_context, APIContext
from portal.libs.contexts.user_context import get_user_context, UserContext
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.models import PortalUser, PortalUserProfile, PortalThirdPartyProvider, PortalUserThirdPartyAuth
from portal.schemas.auth import FirebaseTokenPayload
from portal.schemas.user import SUserThirdParty, SAuthProvider
from portal.serializers.v1.account import AccountLogin, AccountUpdate, LoginResponse, AccountDetail


class UserHandler:
    """UserHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        fcm_device_handler: FCMDeviceHandler,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self.fcm_device_handler = fcm_device_handler
        # contexts
        self._api_context: APIContext = get_api_context()
        self._user_ctx: UserContext = get_user_context()

    @staticmethod
    async def verify_login_token(token: str) -> FirebaseTokenPayload:
        """
        Verify login token
        :param token:
        :return:
        """
        auth_handler = AuthHandler()
        scheme, credentials = get_authorization_scheme_param(token)
        try:
            return await auth_handler.verify_firebase_token(token=credentials)
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            raise ApiBaseException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    async def login(self, model: AccountLogin) -> LoginResponse:
        """
        Login
        :param model:
        :return:
        """
        match model.login_method:
            case AuthProvider.FIREBASE:
                return await self.firebase_login(model=model)
            case _:
                raise ApiBaseException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid login method")

    @distributed_trace()
    async def firebase_login(self, model: AccountLogin) -> LoginResponse:
        """
        Firebase login
        :param model:
        :return:
        """
        token_payload: FirebaseTokenPayload = await self.verify_login_token(model.firebase_token)
        provider: Optional[SAuthProvider] = await self.get_provider_by_name(AuthProvider.FIREBASE.value)
        user: Optional[SUserThirdParty] = await self.get_user_detail_by_provider_uid(token_payload.user_id)
        if user:
            await (
                self._session.update(PortalUserThirdPartyAuth)
                .values(
                    additional_data=token_payload.model_dump(
                        exclude={"name", "email", "phone_number", "exp", "iat", "user_id"}
                    )
                )
                .where(PortalUserThirdPartyAuth.user_id == user.id)
                .where(PortalUserThirdPartyAuth.provider_id == provider.id)
                .where(PortalUserThirdPartyAuth.provider_uid == token_payload.user_id)
                .execute()
            )
            await self.update_last_login_at(user_id=user.id)
            await self.fcm_device_handler.bind_user_device(user_id=user.id, device_id=model.device_id)
            return LoginResponse(id=user.id, verified=True)
        try:
            user_id = await self.create_user(token_payload=token_payload, provider=provider)
            await self.fcm_device_handler.bind_user_device(user_id=user_id, device_id=model.device_id)
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise ApiBaseException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
        else:
            return LoginResponse(id=user_id, verified=True, first_login=True)

    async def create_user(
        self,
        token_payload: FirebaseTokenPayload,
        provider: SAuthProvider,
    ) -> uuid.UUID:
        """

        :param token_payload:
        :param provider:
        :return:
        """
        user_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalUser)
                .values(
                    id=user_id,
                    phone_number=token_payload.phone_number,
                    email=token_payload.email,
                    verified=True,
                    last_login=datetime.now(tz=pytz.UTC),
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
                    additional_data=token_payload.model_dump(
                        exclude={"name", "email", "phone_number", "exp", "iat", "user_id"}
                    ),
                )
                .execute()
            )
            return user_id
        except Exception as e:
            raise e

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

    async def get_user_detail_by_provider_uid(self, provider_uid: str) -> Optional[SUserThirdParty]:
        """
        Get user detail by provider id
        :param provider_uid:
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
            .where(PortalUserThirdPartyAuth.provider_uid == provider_uid)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchrow(as_model=SUserThirdParty)
        )
        if not user:
            return None
        return user

    async def update_last_login_at(self, user_id: uuid.UUID) -> None:
        await (
            self._session.update(PortalUser)
            .values(last_login_at=datetime.now(tz=pytz.UTC))
            .where(PortalUser.id == user_id)
            .execute()
        )

    async def get_user(self, user_id: uuid.UUID) -> AccountDetail:
        """
        Get user detail
        Ticket detail has been removed (maybe integrated in the future with different logic)
        :param user_id:
        :return:
        """
        if user_id != self._user_ctx.user_id:
            raise ApiBaseException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        user: Optional[AccountDetail] = await (
            self._session.select(
                PortalUser.id,
                PortalUser.phone_number,
                PortalUser.email,
                PortalUserProfile.display_name,
                PortalUserProfile.is_ministry.label("volunteer")
            )
            .join(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(PortalUser.id == user_id)
            .fetchrow(as_model=AccountDetail)
        )
        if not user:
            raise NotFoundException(detail=f"User {user_id} not found")
        return user

    async def update_user(self, user_id: uuid.UUID, model: AccountUpdate) -> None:
        """

        :param user_id:
        :param model:
        :return:
        """
        if user_id != self._user_ctx.user_id:
            raise ApiBaseException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        await (
            self._session.update(PortalUser)
            .values(
                display_name=model.display_name
            )
            .where(PortalUser.id == user_id)
            .execute()
        )

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
