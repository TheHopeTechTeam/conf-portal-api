"""
AdminPermissionHandler
"""
from typing import Optional
import sqlalchemy as sa
from uuid import UUID

from redis.asyncio import Redis

from portal.config import settings
from portal.libs.consts.cache_keys import create_permission_key
from portal.libs.database import Session, RedisPool
from portal.models import PortalPermission, PortalVerb, PortalResource, PortalRole, PortalUser, PortalRolePermission
from portal.schemas.permission import PermissionBase
from portal.schemas.user import UserBase


class AdminPermissionHandler:
    """AdminPermissionHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    async def init_user_permissions_cache(self, user: UserBase, expire: int):
        """
        Initialize user permissions cache
        :param user:
        :param expire:
        :return:
        """
        await self.clear_user_permissions_cache(user_id=user.id)
        permissions: Optional[list[PermissionBase]] = await self._get_user_role_permissions(user=user)
        if not permissions:
            return
        key = create_permission_key(str(user.id))
        for permission in permissions:
            permission_code = permission.code
            await self._redis.hset(key, permission_code, permission.model_dump_json())
        await self._redis.expire(key, expire)

    async def clear_user_permissions_cache(self, user_id: UUID):
        """
        Clear user permissions cache
        :param user_id:
        :return:
        """
        key = create_permission_key(str(user_id))
        await self._redis.delete(key)

    async def _get_user_role_permissions(self, user: UserBase) -> Optional[list[PermissionBase]]:
        """
        Get permissions by user role
        :param user:
        :return:
        """
        if user.is_superuser:
            return await self._get_all_permissions()
        return await (
            self._session.select(
                PortalPermission.code,
                PortalVerb.action,
                PortalResource.code.label("resource_code")
            )
            .select_from(PortalUser)
            .join(PortalUser.roles)
            .join(PortalRolePermission, PortalRolePermission.role_id == PortalRole.id)
            .join(PortalPermission, PortalPermission.id == PortalRolePermission.permission_id)
            .join(PortalVerb, PortalPermission.verb_id == PortalVerb.id)
            .join(PortalResource, PortalPermission.resource_id == PortalResource.id)
            .where(PortalUser.id == user.id)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .where(PortalUser.verified == True)
            .where(PortalRole.is_deleted == False)
            .where(PortalRole.is_active == True)
            .where(PortalPermission.is_deleted == False)
            .where(PortalPermission.is_active == True)
            .where(PortalVerb.is_deleted == False)
            .where(PortalVerb.is_active == True)
            .where(PortalResource.is_deleted == False)
            .where(PortalResource.is_visible == True)
            .where(sa.or_(
                PortalRolePermission.expire_date.is_(None),
                PortalRolePermission.expire_date > sa.func.now()
            ))
            .distinct()
            .order_by([
                PortalResource.code,
                PortalVerb.action,
                PortalPermission.code,
            ])
            .fetch(as_model=PermissionBase)
        )


    async def _get_all_permissions(self) -> Optional[list[PermissionBase]]:
        """
        Get all permissions
        :return:
        """
        return await (
            self._session.select(
                PortalPermission.code,
                PortalVerb.action,
                PortalResource.code.label("resource_code")
            )
            .outerjoin(PortalResource, PortalPermission.resource_id == PortalResource.id)
            .outerjoin(PortalVerb, PortalPermission.verb_id == PortalVerb.id)
            .where(PortalPermission.is_active == True)
            .fetch(as_model=PermissionBase)
        )
