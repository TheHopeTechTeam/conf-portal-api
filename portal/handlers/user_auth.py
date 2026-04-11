"""
Handler for authentication
"""
import uuid
from typing import Optional

from pydantic import ValidationError
from redis.asyncio import Redis
from starlette import status

from portal.config import settings
from portal.exceptions.responses import ApiBaseException, UnauthorizedException, NotFoundException, BadRequestException
from portal.handlers.fcm_device import FCMDeviceHandler
from portal.handlers.user import UserHandler
from portal.libs.consts.enums import AuthProvider
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.events.publisher import publish_event_in_background
from portal.libs.events.types import UserTicketSyncEvent, SendSignInLinkEvent
from portal.libs.logger import logger
from portal.models import PortalThirdPartyProvider, PortalUserThirdPartyAuth
from portal.providers.firebase.base import FirebaseProvider
from portal.providers.jwt_provider import JWTProvider
from portal.providers.login_verification_email_provider import LoginVerificationEmailProvider
from portal.providers.refresh_token_provider import RefreshTokenProvider
from portal.providers.third_party_provider import ThirdPartyAuthProvider
from portal.providers.token_blacklist_provider import TokenBlacklistProvider
from portal.schemas.auth import FirebaseTokenPayload
from portal.schemas.base import RefreshTokenData
from portal.schemas.user import SUserThirdParty, SAuthProvider, SUserDetail
from portal.serializers.mixins import TokenResponse, RefreshTokenRequest, LogoutResponse
from portal.serializers.v1.user import UserLogin, UserLoginResponse, UserInfo, UserLocalLogin


class UserAuthHandler:
    """UserAuthHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        jwt_provider: JWTProvider,
        token_blacklist_provider: TokenBlacklistProvider,
        refresh_token_provider: RefreshTokenProvider,
        user_handler: UserHandler,
        fcm_device_handler: FCMDeviceHandler,
        firebase_provider: FirebaseProvider,
        login_verification_email_provider: LoginVerificationEmailProvider,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._jwt_provider = jwt_provider
        self._token_blacklist_provider = token_blacklist_provider
        self._refresh_token_provider = refresh_token_provider
        self._user_handler = user_handler
        self.fcm_device_handler = fcm_device_handler
        self._third_party_provider = ThirdPartyAuthProvider()
        self._firebase_provider = firebase_provider
        self._login_verification_email_provider = login_verification_email_provider

    async def local_login(self, model: UserLocalLogin) -> UserLoginResponse:
        """
        Simulate login
        :param model:
        :return:
        """
        user: Optional[SUserThirdParty] = await self._user_handler.get_user_tp_detail_by_email(email=model.email)
        if not user:
            raise NotFoundException(detail="User not found")
        device_id = await self.fcm_device_handler.bind_user_device(user_id=user.id, device_key=model.device_id)
        user_info = UserInfo(
            id=user.id,
            phone_number=user.phone_number,
            email=user.email,
            display_name=user.display_name,
            volunteer=user.is_ministry,
            verified=user.verified,
        )
        token = await self.get_token_info(user=user, device_id=device_id)
        publish_event_in_background(UserTicketSyncEvent(user_id=user.id, email=user.email))
        return UserLoginResponse(user=user_info, token=token)

    @distributed_trace()
    async def login(self, model: UserLogin) -> UserLoginResponse:
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
    async def firebase_login(self, model: UserLogin) -> UserLoginResponse:
        """
        Firebase login
        :param model:
        :return:
        """
        token_payload: FirebaseTokenPayload = self._third_party_provider.verify_firebase_token(token=model.firebase_token)
        email_verified = token_payload.email_verified if token_payload.email else False
        if token_payload.email and token_payload.email.lower() != settings.FIREBASE_TEST_EMAIL and not email_verified:
            raise ApiBaseException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not verified or invalid login method")
        if not token_payload.email:
            raise ApiBaseException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")
        provider: Optional[SAuthProvider] = await self.get_provider_by_name(AuthProvider.FIREBASE.value)
        if not provider:
            logger.error("Auth provider not configured")
            raise ApiBaseException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth provider not configured")
        user: Optional[SUserThirdParty] = await self._user_handler.get_user_detail_by_provider_info(
            provider_uid=token_payload.user_id,
            email=token_payload.email
        )
        is_first_login = False
        if not user:
            user = await self._user_handler.get_user_tp_detail_by_email(email=token_payload.email)
            is_first_login = bool(user)
        if user:
            try:
                user = await self._prepare_firebase_login_user(
                    user=user,
                    provider=provider,
                    token_payload=token_payload,
                )
                return await self._build_login_response(
                    user=user,
                    device_key=model.device_id,
                    first_login=is_first_login,
                )
            except Exception as e:
                logger.exception(e)
                raise ApiBaseException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
        else:
            try:
                user = await self._user_handler.create_user(token_payload=token_payload, provider=provider)
                return await self._build_login_response(
                    user=user,
                    device_key=model.device_id,
                    first_login=True,
                )
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                raise ApiBaseException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

    @distributed_trace()
    async def _prepare_firebase_login_user(
        self,
        user: SUserThirdParty,
        provider: SAuthProvider,
        token_payload: FirebaseTokenPayload,
    ) -> SUserThirdParty:
        await (
            self._session.insert(PortalUserThirdPartyAuth)
            .values(
                user_id=user.id,
                provider_id=provider.id,
                provider_uid=token_payload.user_id,
                additional_data=token_payload.model_dump_json(
                    exclude={"name", "email", "phone_number", "exp", "iat", "user_id"}
                ),
            )
            .on_conflict_do_update(
                index_elements=["user_id", "provider_id", "provider_uid"],
                set_={
                    "additional_data": token_payload.model_dump_json(
                        exclude={"name", "email", "phone_number", "exp", "iat", "user_id"}
                    )
                },
            )
            .execute()
        )
        await self._user_handler.mark_user_verified(user_id=user.id)
        await self._user_handler.update_last_login_at(user_id=user.id)
        refreshed_user = await self._user_handler.get_user_tp_detail_by_email(email=user.email)
        if not refreshed_user:
            raise ApiBaseException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
        return refreshed_user

    @distributed_trace()
    async def _build_login_response(
        self,
        user: SUserThirdParty,
        device_key: str,
        first_login: bool = False,
    ) -> UserLoginResponse:
        device_id = await self.fcm_device_handler.bind_user_device(user_id=user.id, device_key=device_key)
        user_info = UserInfo(
            id=user.id,
            phone_number=user.phone_number,
            email=user.email,
            display_name=user.display_name,
            volunteer=user.is_ministry,
            verified=user.verified,
            first_login=first_login,
        )
        token = await self.get_token_info(user=user, device_id=device_id)
        if user.email:
            publish_event_in_background(UserTicketSyncEvent(user_id=user.id, email=user.email))
        return UserLoginResponse(user=user_info, token=token)

    @distributed_trace()
    async def get_token_info(self, user: SUserThirdParty, device_id: uuid.UUID) -> TokenResponse:
        """

        :return:
        """
        family_id = uuid.uuid4()

        # Create access token with family id
        access_token = self._jwt_provider.create_access_token(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            family_id=family_id,
        )
        # Issue opaque refresh token bound to device and family
        try:
            refresh_token = await self._refresh_token_provider.issue(
                user_id=user.id,
                device_id=device_id,
                family_id=family_id,
            )
        except Exception as exc:
            logger.exception(exc)
            raise UnauthorizedException(debug_detail=str(exc))
        else:
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=self._jwt_provider.access_token_expire_minutes * 60
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
    async def refresh_token(self, refresh_data: RefreshTokenRequest) -> TokenResponse:
        """
        Refresh admin access token
        :param refresh_data:
        :return:
        """
        try:
            refresh_token_data: tuple[str, RefreshTokenData] = await self._refresh_token_provider.rotate(
                refresh_token=refresh_data.refresh_token
            )
            refresh_token, rt_data = refresh_token_data
        except Exception as exc:
            raise UnauthorizedException(
                detail="Invalid refresh token",
                debug_detail=str(exc)
            )

        user: Optional[SUserDetail] = await self._user_handler.get_user_detail_by_id(rt_data.user_id)
        if not user:
            raise UnauthorizedException(
                detail="User not found",
                debug_detail=f"User not found for id: {rt_data.user_id}"
            )
        # Create new access token with same family id
        access_token = self._jwt_provider.create_access_token(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            family_id=rt_data.family_id
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._jwt_provider.access_token_expire_minutes * 60
        )

    @distributed_trace()
    async def send_signin_link(
        self,
        email: str,
    ) -> None:
        """
        Publish send sign-in link event in background.
        :param email: Recipient email address.
        """
        publish_event_in_background(SendSignInLinkEvent(email=email))

    @distributed_trace()
    async def logout(self, access_token: str, refresh_token: str = None) -> LogoutResponse:
        """
        Logout admin user: blacklist AT and revoke RT family via provider
        :param access_token:
        :param refresh_token:
        :return:
        """
        try:
            if not self._token_blacklist_provider:
                raise ApiBaseException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
            # Get token expiration
            access_exp = self._jwt_provider.get_token_expiration(access_token)
            if access_exp:
                await self._token_blacklist_provider.add_to_blacklist(access_token, access_exp)
            # Revoke refresh token (and family)
            if refresh_token:
                await self._refresh_token_provider.revoke_by_token(refresh_token, revoke_family=True)
            return LogoutResponse(message="Successfully logged out")
        except ValidationError as ve:
            logger.warning(f"Token validation error during logout: {ve}")
            raise BadRequestException(detail="Invalid token format")
        except Exception as e:
            logger.error(f"Error logging out: {e}")
            raise ApiBaseException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
