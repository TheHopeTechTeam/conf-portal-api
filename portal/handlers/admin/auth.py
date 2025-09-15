"""
Admin authentication handlers
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from pydantic import EmailStr
from redis.asyncio import Redis

from portal.config import settings
from portal.libs.contexts.user_context import get_user_context, UserContext
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalUser
from portal.providers.jwt_provider import JWTProvider
from portal.providers.password_provider import PasswordProvider
from portal.providers.refresh_token_provider import RefreshTokenProvider
from portal.providers.token_blacklist_provider import TokenBlacklistProvider
from portal.schemas.base import RefreshTokenData
from portal.schemas.user import UserDetail
from portal.serializers.v1.admin.auth import (
    AdminLoginRequest,
    AdminTokenResponse,
    AdminInfo,
    AdminLoginResponse, RefreshTokenRequest,
)
from .permission import AdminPermissionHandler
from .role import AdminRoleHandler
from .user import AdminUserHandler


class AdminAuthHandler:
    """Admin authentication handler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        jwt_provider: JWTProvider,
        password_provider: PasswordProvider,
        token_blacklist_provider: TokenBlacklistProvider,
        refresh_token_provider: RefreshTokenProvider,
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
        # handlers
        self._admin_permission_handler = admin_permission_handler
        self._admin_role_handler = admin_role_handler
        self._admin_user_handler = admin_user_handler

        try:
            self._user_ctx: Optional[UserContext] = get_user_context()
        except Exception:
            self._user_ctx = None

    @distributed_trace()
    async def authenticate_admin(self, email: EmailStr, password: str) -> Optional[UserDetail]:
        """
        Authenticate admin user with email and password
        """
        # Find user by email
        user: UserDetail = await self._admin_user_handler.get_user_detail_by_email(email)
        if not user:
            return None

        if not self._password_provider.verify_password(password, user.password_hash):
            return None

        if not user.is_admin and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have admin privileges"
            )

        return user

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
    async def login(self, login_data: AdminLoginRequest, device_id: UUID) -> AdminLoginResponse:
        """
        Admin login
        :param login_data:
        :param device_id:
        :return:
        """
        # Authenticate admin
        user: UserDetail = await self.authenticate_admin(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Get admin roles and permissions
        roles = await self._admin_role_handler.init_user_roles_cache(user, self._expires_in)
        permissions = await self._admin_permission_handler.init_user_permissions_cache(user, self._expires_in)

        # Update last login
        last_login_at = datetime.now(timezone.utc)
        await self.update_last_login(user.id, last_login_at)

        # Generate family id for this login chain
        family_id = uuid4()

        # Create access token with family id
        access_token = self._jwt_provider.create_admin_access_token(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            roles=roles,
            permissions=permissions,
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

        token = AdminTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._jwt_provider.access_token_expire_minutes * 60
        )

        return AdminLoginResponse(admin=admin_info, token=token)

    async def refresh_token(self, refresh_data: RefreshTokenRequest) -> AdminTokenResponse:
        """
        Refresh admin access token
        :param refresh_data:
        :return:
        """
        try:
            refresh_token, rt_data = await self._refresh_token_provider.rotate(refresh_token=refresh_data.refresh_token)  # type: str, RefreshTokenData
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

        user: UserDetail = await self._admin_user_handler.get_user_detail_by_id(rt_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Get admin roles and permissions
        roles = await self._admin_role_handler.init_user_roles_cache(user, self._expires_in)
        permissions = await self._admin_permission_handler.init_user_permissions_cache(user, self._expires_in)

        # Create new access token with same family id
        access_token = self._jwt_provider.create_admin_access_token(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            roles=roles,
            permissions=permissions,
            family_id=rt_data.family_id
        )

        # no blacklist; rotation handles invalidation

        return AdminTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._jwt_provider.access_token_expire_minutes * 60
        )

    async def get_me(self) -> AdminInfo:
        """

        :return:
        """
        if not self._user_ctx:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        user: UserDetail = await self._admin_user_handler.get_user_detail_by_id(user_id=self._user_ctx.user_id)
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

    async def logout(self, access_token: str, refresh_token: str = None) -> bool:
        """
        Logout admin user: blacklist AT and revoke RT family via provider
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
        except Exception:
            return False
