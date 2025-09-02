"""
AdminRoleHandler
"""
from typing import Optional, Union
from uuid import UUID

from redis.asyncio import Redis

from portal.config import settings
from portal.libs.consts.cache_keys import create_user_role_key
from portal.libs.database import Session, RedisPool
from portal.models import PortalRole, PortalUser
from portal.schemas.user import UserBase, UserDetail


class AdminRoleHandler:
    """AdminRoleHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    async def init_user_roles_cache(self, user: Union[UserBase, UserDetail], expire: int) -> Optional[list[str]]:
        """
        Initialize user roles cache
        :param user:
        :param expire:
        :return:
        """
        await self.clear_user_roles_cache(user_id=user.id)
        role_codes = await self._session.select(PortalRole.code) \
            .join(PortalRole.users) \
            .where(PortalUser.id == user.id) \
            .where(PortalRole.is_deleted == False) \
            .where(PortalUser.is_deleted == False) \
            .order_by(PortalRole.code) \
            .fetchvals()
        if user.is_superuser:
            role_codes = ["superadmin"]
        if not role_codes:
            return None
        key = create_user_role_key(str(user.id))
        await self._redis.sadd(key, *role_codes)
        await self._redis.expire(key, expire)
        return role_codes

    async def clear_user_roles_cache(self, user_id: UUID):
        """
        Clear user roles cache
        :param user_id:
        :return:
        """
        key = create_user_role_key(str(user_id))
        await self._redis.delete(key)
