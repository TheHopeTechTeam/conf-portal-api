"""
AdminUserHandler
"""
from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from pydantic import EmailStr
from redis.asyncio import Redis

from portal.config import settings
from portal.libs.database import Session, RedisPool
from portal.models import PortalUser, PortalUserProfile
from portal.schemas.user import SUserSensitive
from portal.serializers.mixins import GenericQueryBaseModel
from portal.serializers.v1.admin.user import UserTableItem, UserPages


class AdminUserHandler:
    """AdminUserHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    async def get_user_detail_by_email(self, email: EmailStr) -> Optional[SUserSensitive]:
        """

        :param email:
        :return:
        """
        user: SUserSensitive = await (
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
            .fetchrow(as_model=SUserSensitive)
        )
        if not user:
            return None
        return user

    async def get_user_detail_by_id(self, user_id: UUID) -> Optional[SUserSensitive]:
        """
        Get user detail by id
        :param user_id:
        :return:
        """
        user: SUserSensitive = await (
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
            .where(PortalUser.id == user_id)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchrow(as_model=SUserSensitive)
        )
        if not user:
            return None
        return user

    async def get_user_pages(self, model: GenericQueryBaseModel):
        """
        Get user pages
        :param model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalUser.id,
                PortalUser.phone_number,
                PortalUser.email,
                PortalUser.verified,
                PortalUser.is_active,
                PortalUser.is_superuser,
                PortalUser.is_admin,
                PortalUser.created_at,
                PortalUser.updated_at,
                PortalUser.last_login_at,
                PortalUser.remark,
                PortalUserProfile.display_name,
                PortalUserProfile.is_ministry,
                PortalUserProfile.description
            )
            .join(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(PortalUser.is_deleted == model.deleted)
            .where(
                model.keyword, lambda: sa.or_(
                    PortalUser.phone_number.ilike(f"%{model.keyword}%"),
                    PortalUser.email.ilike(f"%{model.keyword}%"),
                    PortalUserProfile.display_name.ilike(f"%{model.keyword}%")
                )
            )
            .order_by_with(
                tables=[PortalUser, PortalUserProfile],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=UserTableItem
            )
        )  # type: (list[UserTableItem], int)

        return UserPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )
