"""
Admin authentication handlers
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import EmailStr
from redis.asyncio import Redis

from portal.config import settings
from portal.handlers import AdminPermissionHandler
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalUserProfile
from portal.models.rbac import PortalUser, PortalRole, PortalPermission, PortalResource, PortalVerb
from portal.providers.jwt_provider import JWTProvider
from portal.providers.password_provider import PasswordProvider
from portal.providers.token_blacklist_provider import TokenBlacklistProvider
from portal.schemas.user import UserDetail, UserBase
from portal.serializers.v1.admin.auth import (
    AdminLoginRequest,
    AdminTokenResponse,
    AdminInfo,
    AdminLoginResponse,
)


class AdminAuthHandler:
    """Admin authentication handler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        jwt_provider: JWTProvider,
        password_provider: PasswordProvider,
        token_blacklist_provider: TokenBlacklistProvider,
        admin_permission_handler: AdminPermissionHandler
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._jwt_provider = jwt_provider
        self._password_provider = password_provider
        self._token_blacklist_provider = token_blacklist_provider
        self._admin_permission_handler = admin_permission_handler
        self._expires_in = 60 * 60 * 24  # 24 hours

    @distributed_trace()
    async def authenticate_admin(self, email: EmailStr, password: str) -> Optional[UserDetail]:
        """
        Authenticate admin user with email and password
        """
        # Find user by email
        user: UserDetail = await (
            self._session.select(
                PortalUser.id,
                PortalUser.phone_number,
                PortalUser.email,
                PortalUser.password_hash,
                PortalUser.verified,
                PortalUser.is_active,
                PortalUser.is_superuser,
                PortalUser.is_admin,
                PortalUser.password_changed_at,
                PortalUser.password_expires_at,
                PortalUser.last_login_at,
                PortalUserProfile.display_name,
                PortalUserProfile.gender,
                PortalUserProfile.is_ministry,
            )
            .join(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(PortalUser.email == email)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchrow(as_model=UserDetail)
        )

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
    async def get_admin_roles_and_permissions(self, user_id: UUID) -> tuple[list[str], list[str]]:
        """
        Get admin user roles and permissions
        """
        # Get user to check admin status
        user: UserBase = await self._session.select(PortalUser).where(PortalUser.id == user_id).fetchrow(as_model=UserBase)
        if not user:
            return [], []

        # If superuser, return all permissions
        if user.is_superuser:
            all_permissions = await (
                self._session.select(
                    PortalPermission.display_name.label("name")
                )
                .join(PortalResource, PortalPermission.resource_id == PortalResource.id)
                .join(PortalVerb, PortalPermission.verb_id == PortalVerb.id)
                .where(PortalPermission.is_active == True)
                .where(PortalVerb.is_active == True)
                .fetch()
            )

            permissions = [row["name"] for row in all_permissions]
            permissions.sort()
            return ["superuser"], permissions

        # If admin, get roles and permissions from RBAC
        if user["is_admin"]:
            # Get user roles
            roles_result = await (
                self._session.select(PortalRole.name)
                .join(PortalRole.users)
                .where(PortalUser.id == user_id)
                .where(PortalRole.is_active == True)
                .fetch()
            )

            roles = [row["name"] for row in roles_result]

            # Get user permissions
            permissions_result = await (
                self._session.select(PortalPermission.display_name.label("name"))
                .join(PortalResource, PortalPermission.resource_id == PortalResource.id)
                .join(PortalVerb, PortalPermission.verb_id == PortalVerb.id)
                .join(PortalPermission.roles)
                .join(PortalRole.users)
                .where(PortalUser.id == user_id)
                .where(PortalRole.is_active == True)
                .where(PortalPermission.is_active == True)
                .where(PortalResource.is_visible == True)
                .where(PortalVerb.is_active == True)
                .fetch()
            )

            permissions = [row["name"] for row in permissions_result]

            return roles, permissions

        return [], []

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
        await self._session.commit()

    @distributed_trace()
    async def login(self, login_data: AdminLoginRequest) -> AdminLoginResponse:
        """
        Admin login
        """
        # Authenticate admin
        user: UserDetail = await self.authenticate_admin(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Get admin roles and permissions
        await self._admin_permission_handler.init_user_permissions_cache(user, self._expires_in)
        roles, permissions = await self.get_admin_roles_and_permissions(user.id)

        # Update last login
        last_login_at = datetime.now(timezone.utc)
        await self.update_last_login(user.id, last_login_at)

        # Create tokens
        access_token = self._jwt_provider.create_admin_access_token(
            subject=str(user.id),
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            roles=roles,
            permissions=permissions
        )

        refresh_token = self._jwt_provider.create_admin_refresh_token(
            subject=str(user.id),
            user_id=user.id
        )

        # Create response
        admin_info = AdminInfo(
            id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            roles=roles,
            permissions=permissions,
            last_login_at=last_login_at
        )

        tokens = AdminTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._jwt_provider.access_token_expire_minutes * 60
        )

        return AdminLoginResponse(admin=admin_info, tokens=tokens)

    async def refresh_token(self, refresh_token: str) -> AdminTokenResponse:
        """
        Refresh admin access token with blacklist check
        """
        # Verify refresh token with blacklist check
        payload = await self._jwt_provider.verify_refresh_token_with_blacklist(refresh_token)
        if not payload or payload.get("type") != "admin_refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or blacklisted refresh token"
            )

        user_id = UUID(payload.get("user_id"))

        # Get user
        user: UserDetail = await (
            self._session.select(PortalUser)
            .where(PortalUser.id == user_id)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchrow(UserDetail)
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Get admin roles and permissions
        roles, permissions = await self.get_admin_roles_and_permissions(user.id)

        # Create new access token
        access_token = self._jwt_provider.create_admin_access_token(
            subject=str(user.id),
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            roles=roles,
            permissions=permissions
        )

        # Create new refresh token
        new_refresh_token = self._jwt_provider.create_admin_refresh_token(
            subject=str(user.id),
            user_id=user.id
        )

        # Blacklist the old refresh token
        if self._token_blacklist_provider:
            old_refresh_exp = self._jwt_provider.get_token_expiration(refresh_token)
            if old_refresh_exp:
                await self._token_blacklist_provider.add_refresh_token_to_blacklist(refresh_token, old_refresh_exp)

        return AdminTokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=self._jwt_provider.access_token_expire_minutes * 60
        )

    async def get_current_admin_from_token(self, token: str) -> Optional[dict]:
        """
        Get current admin from JWT token with blacklist check
        """
        payload = await self._jwt_provider.verify_token_with_blacklist(token)
        if not payload or payload.get("type") != "admin_access":
            return None

        user_id = UUID(payload.get("user_id"))

        user = await (
            self._session.select(PortalUser)
            .where(PortalUser.id == user_id)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchrow()
        )

        return user

    async def logout(self, access_token: str, refresh_token: str = None) -> bool:
        """
        Logout admin user by blacklisting tokens
        """
        try:
            if not self._token_blacklist_provider:
                return False

            # Get token expiration
            access_exp = self._jwt_provider.get_token_expiration(access_token)
            if access_exp:
                await self._token_blacklist_provider.add_to_blacklist(access_token, access_exp)

            # Blacklist refresh token if provided
            if refresh_token:
                refresh_exp = self._jwt_provider.get_token_expiration(refresh_token)
                if refresh_exp:
                    await self._token_blacklist_provider.add_refresh_token_to_blacklist(refresh_token, refresh_exp)

            return True
        except Exception:
            return False
