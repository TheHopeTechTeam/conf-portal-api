"""
Admin authentication handlers
"""
import abc
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import UnauthorizedException, ForbiddenException, BadRequestException
from portal.libs.consts.enums import AccessTokenAudType
from portal.libs.contexts.request_context import RequestContext, get_request_context
from portal.libs.contexts.user_context import get_user_context, UserContext
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.libs.smtp_client import smtp_client
from portal.models import PortalUser
from portal.providers.jwt_provider import JWTProvider
from portal.providers.password_provider import PasswordProvider
from portal.providers.password_reset_token_provider import PasswordResetTokenProvider
from portal.providers.refresh_token_provider import RefreshTokenProvider
from portal.providers.template_render_provider import TemplateRenderProvider
from portal.providers.token_blacklist_provider import TokenBlacklistProvider
from portal.schemas.base import RefreshTokenData
from portal.schemas.user import SUserSensitive
from portal.serializers.mixins import TokenResponse, RefreshTokenRequest
from portal.serializers.v1.admin.auth import (
    AdminLoginRequest,
    AdminInfo,
    AdminLoginResponse,
    AdminRequestPasswordResetRequest,
    AdminResetPasswordWithTokenRequest,
)
from .permission import AdminPermissionHandler
from .role import AdminRoleHandler
from .user import AdminUserHandler


class PasswordValidator(abc.ABC):

    @abc.abstractmethod
    async def validate(self, login_data: AdminLoginRequest, user: SUserSensitive) -> None:
        pass


class AdminAuthHandler(PasswordValidator):
    """Admin authentication handler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        jwt_provider: JWTProvider,
        password_provider: PasswordProvider,
        token_blacklist_provider: TokenBlacklistProvider,
        refresh_token_provider: RefreshTokenProvider,
        password_reset_token_provider: PasswordResetTokenProvider,
        admin_permission_handler: AdminPermissionHandler,
        admin_role_handler: AdminRoleHandler,
        admin_user_handler: AdminUserHandler,
    ):
        self._expires_in = 60 * 60 * 24  # 24 hours
        # db
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        # providers
        self._jwt_provider = jwt_provider
        self._password_provider = password_provider
        self._token_blacklist_provider = token_blacklist_provider
        self._refresh_token_provider = refresh_token_provider
        self._password_reset_token_provider = password_reset_token_provider
        # handlers
        self._admin_permission_handler = admin_permission_handler
        self._admin_role_handler = admin_role_handler
        self._admin_user_handler = admin_user_handler
        # context
        self._user_ctx: Optional[UserContext] = get_user_context()
        self._req_ctx: Optional[RequestContext] = get_request_context()

    @distributed_trace()
    async def validate(self, login_data: AdminLoginRequest, user: SUserSensitive) -> None:
        """

        :param login_data:
        :param user:
        :return:
        """
        if not user.is_admin:
            raise ForbiddenException(detail="User does not have admin privileges")
        if not user.verified or not user.is_active:
            raise UnauthorizedException()
        # TODO: Implement GAC Authenticator
        if not self._password_provider.verify_password(login_data.password, user.password_hash):
            await self.record_login_fail(user)
            raise UnauthorizedException(detail="Invalid password")

    @distributed_trace()
    async def record_login_fail(self, user: SUserSensitive):
        """
        TODO: Record login failure for user
        :param user:
        :return:
        """

    @distributed_trace()
    async def login_without_validate(self, login_data: AdminLoginRequest, device_id: UUID) -> AdminLoginResponse:
        user: SUserSensitive = await self._admin_user_handler.get_user_detail_by_email(login_data.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return await self.login_by_user(user=user, device_id=device_id)

    @distributed_trace()
    async def login(self, login_data: AdminLoginRequest, device_id: UUID) -> AdminLoginResponse:
        user: SUserSensitive = await self._admin_user_handler.get_user_detail_by_email(login_data.email)
        if not user:
            raise UnauthorizedException()
        await self.validate(login_data, user)
        return await self.login_by_user(user=user, device_id=device_id)

    @distributed_trace()
    async def login_by_user(self, user: SUserSensitive, device_id: UUID) -> AdminLoginResponse:
        """
        Admin login
        :param user:
        :param device_id:
        :return:
        """
        # Get admin roles and permissions
        roles = await self._admin_role_handler.init_user_roles_cache(user, self._expires_in)
        permissions = await self._admin_permission_handler.init_user_permissions_cache(user, self._expires_in)

        if not roles or not permissions:
            raise UnauthorizedException(detail="User does not have been assigned any roles.\nPlease contact system administrator.")

        # Update last login
        last_login_at = datetime.now(timezone.utc)
        await self.update_last_login(user.id, last_login_at)

        # Generate family id for this login chain
        family_id = uuid4()

        # Create access token with family id
        access_token = self._jwt_provider.create_access_token(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            roles=roles,
            permissions=permissions,
            family_id=family_id,
            aud_type=AccessTokenAudType.ADMIN,
        )
        # Issue opaque refresh token bound to device and family
        try:
            refresh_token = await self._refresh_token_provider.issue(
                user_id=user.id,
                device_id=device_id,
                family_id=family_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

        # Create response
        admin_info = AdminInfo(
            id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            roles=roles,
            permissions=permissions,
            last_login_at=last_login_at
        )

        token = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._jwt_provider.access_token_expire_minutes * 60
        )

        return AdminLoginResponse(admin=admin_info, token=token)

    @distributed_trace()
    async def update_last_login(self, user_id: UUID, last_login_at: Optional[datetime] = None) -> None:
        """
        Update admin's last login timestamp
        """
        if last_login_at is None:
            last_login_at = datetime.now(timezone.utc)
        await (
            self._session.update(PortalUser)
            .where(PortalUser.id == user_id)
            .values(last_login_at=last_login_at)
            .execute()
        )

    @distributed_trace()
    async def refresh_token(self, refresh_data: RefreshTokenRequest) -> TokenResponse:
        """
        Refresh admin access token
        :param refresh_data:
        :return:
        """
        try:
            refresh_token, rt_data = await self._refresh_token_provider.rotate(refresh_token=refresh_data.refresh_token)  # type: str, RefreshTokenData
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

        user: SUserSensitive = await self._admin_user_handler.get_user_detail_by_id(rt_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Get admin roles and permissions
        roles = await self._admin_role_handler.init_user_roles_cache(user, self._expires_in)
        permissions = await self._admin_permission_handler.init_user_permissions_cache(user, self._expires_in)

        # Create new access token with same family id
        access_token = self._jwt_provider.create_access_token(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            roles=roles,
            permissions=permissions,
            family_id=rt_data.family_id,
            aud_type=AccessTokenAudType.ADMIN
        )

        # no blacklist; rotation handles invalidation
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._jwt_provider.access_token_expire_minutes * 60
        )

    @distributed_trace()
    async def get_me(self) -> AdminInfo:
        """

        :return:
        """
        if not self._user_ctx:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        user: SUserSensitive = await self._admin_user_handler.get_user_detail_by_id(user_id=self._user_ctx.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        roles = await self._admin_role_handler.init_user_roles_cache(user, self._expires_in)
        permissions = await self._admin_permission_handler.init_user_permissions_cache(user, self._expires_in)

        return AdminInfo(
            id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            roles=roles,
            permissions=permissions,
            last_login_at=user.last_login_at
        )

    @distributed_trace()
    async def logout(self, access_token: str, refresh_token: str = None) -> bool:
        """
        Logout admin user: blacklist AT and revoke RT family via provider
        :param access_token:
        :param refresh_token:
        :return:
        """
        try:
            if not self._token_blacklist_provider:
                return False
            # Get token expiration
            access_exp = self._jwt_provider.get_token_expiration(access_token)
            if access_exp:
                await self._token_blacklist_provider.add_to_blacklist(access_token, access_exp)
            # Revoke refresh token (and family)
            if refresh_token:
                await self._refresh_token_provider.revoke_by_token(refresh_token, revoke_family=True)
            return True
        except Exception as e:
            logger.error(f"Error logging out: {e}")
            return False

    @distributed_trace()
    async def request_password_reset(self, model: AdminRequestPasswordResetRequest) -> None:
        """
        Request password reset
        :param model:
        :return:
        """
        user: SUserSensitive = await self._admin_user_handler.get_user_detail_by_email(model.email)

        # Always return success to prevent email enumeration
        if not user:
            logger.warning(f"Password reset requested for non-existent email: {model.email}")
            raise BadRequestException(detail="Email not found")

        # Generate reset token
        ip_address = self._req_ctx.ip or self._req_ctx.client_ip
        user_agent = self._req_ctx.user_agent
        reset_token = await self._password_reset_token_provider.create_token(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        reset_password_html = await self._generate_password_reset_template(user=user, reset_token=reset_token)

        await (
            smtp_client.create()
            .add_to(model.email)
            .subject("Password Reset Requested")
            .html(reset_password_html)
            .asend()
        )

    @staticmethod
    async def _generate_password_reset_template(user: SUserSensitive, reset_token: str) -> str:
        """

        :param user:
        :param reset_token:
        :return:
        """
        reset_link = f"{settings.ADMIN_PORTAL_URL}/reset-password?token={reset_token}&email={user.email}"
        template_render_provider = TemplateRenderProvider()
        reset_password_html = await template_render_provider.render_email_by_file(
            name="reset_password.html",
            display_name=user.display_name or user.email,
            reset_link=reset_link,
            expiry_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
            current_year=datetime.now(timezone.utc).year,
        )
        return reset_password_html

    @distributed_trace()
    async def reset_password(self, model: AdminResetPasswordWithTokenRequest) -> None:
        """
        Reset password
        :param model:
        :return:
        """
        if model.new_password != model.new_password_confirm:
            raise BadRequestException(detail="Passwords do not match")

        if not self._password_provider.validate_password(model.new_password):
            raise BadRequestException(detail="Password does not meet complexity requirements")

        user_id = await self._password_reset_token_provider.verify_token(model.token)
        if not user_id:
            raise BadRequestException(detail="Invalid or expired reset token")

        await self._admin_user_handler.reset_password(user_id=user_id, new_password=model.new_password)
        if not await self._password_reset_token_provider.mark_token_as_used(model.token):
            raise BadRequestException(detail="Invalid or expired reset token")
