"""
AdminUserHandler
"""
import uuid
from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from pydantic import EmailStr
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses.base import ApiBaseException, ConflictErrorException
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalUser, PortalUserProfile
from portal.schemas.mixins import UUIDBaseModel
from portal.schemas.user import SUserSensitive
from portal.serializers.mixins.base import DeleteBaseModel
from portal.serializers.v1.admin.user import UserCreate, UserTableItem, UserPages, UserUpdate, UserItem, UserQuery


class AdminUserHandler:
    """AdminUserHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @distributed_trace()
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

    @distributed_trace()
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

    @distributed_trace()
    async def get_user_pages(self, model: UserQuery):
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
                PortalUserProfile.gender,
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
            .where(model.verified is not None, lambda: PortalUser.verified == model.verified)
            .where(model.is_active is not None, lambda: PortalUser.is_active == model.is_active)
            .where(model.is_admin is not None, lambda: PortalUser.is_admin == model.is_admin)
            .where(model.is_superuser is not None, lambda: PortalUser.is_superuser == model.is_superuser)
            .where(model.is_ministry is not None, lambda: PortalUserProfile.is_ministry == model.is_ministry)
            .where(model.gender is not None, lambda: PortalUserProfile.gender == model.gender)
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

    @distributed_trace()
    async def get_user_by_id(self, user_id: UUID) -> Optional[UserItem]:
        """
        Get user by ID
        :param user_id:
        :return:
        """
        user = await (
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
                PortalUserProfile.gender,
                PortalUserProfile.is_ministry,
                PortalUserProfile.description
            )
            .join(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(PortalUser.id == user_id)
            .where(PortalUser.is_deleted == False)
            .fetchrow(as_model=UserItem)
        )
        return user

    @distributed_trace()
    async def create_user(self, model: UserCreate) -> UUIDBaseModel:
        """
        Create user
        :param model:
        :return:
        """
        user_id = uuid.uuid4()
        try:
            # Create PortalUser
            user_fields = {
                "id": user_id,
                "phone_number": model.phone_number,
                "email": model.email,
                "verified": model.verified,
                "is_active": model.is_active,
                "is_superuser": model.is_superuser,
                "is_admin": model.is_admin,
                "remark": model.remark,
            }

            await (
                self._session.insert(PortalUser)
                .values(**user_fields)
                .execute()
            )

            # Create PortalUserProfile
            profile_fields = {
                "user_id": user_id,
                "display_name": model.display_name,
                "gender": model.gender,
                "is_ministry": model.is_ministry,
            }

            await (
                self._session.insert(PortalUserProfile)
                .values(**profile_fields)
                .execute()
            )

        except UniqueViolationError as e:
            raise ConflictErrorException(detail="User already exists", debug_detail=str(e))
        except Exception as e:
            raise ApiBaseException(status_code=500, detail="Internal Server Error", debug_detail=str(e))
        else:
            return UUIDBaseModel(id=user_id)

    @distributed_trace()
    async def update_user(self, user_id: UUID, model: UserUpdate) -> None:
        """
        Update user
        :param user_id:
        :param model:
        :return:
        """
        try:
            # Update PortalUser
            user_fields = {
                "phone_number": model.phone_number,
                "email": model.email,
                "verified": model.verified,
                "is_active": model.is_active,
                "is_superuser": model.is_superuser,
                "is_admin": model.is_admin,
                "remark": model.remark,
            }

            if user_fields:
                result = await (
                    self._session.update(PortalUser)
                    .values(**user_fields, updated_at=sa.func.now())
                    .where(PortalUser.id == user_id)
                    .execute()
                )
                if result == 0:
                    raise ApiBaseException(status_code=404, detail="User not found")

            # Update PortalUserProfile
            profile_fields = {
                "display_name": model.display_name,
                "gender": model.gender,
                "is_ministry": model.is_ministry,
            }

            if profile_fields:
                await (
                    self._session.update(PortalUserProfile)
                    .values(**profile_fields, updated_at=sa.func.now())
                    .where(PortalUserProfile.user_id == user_id)
                    .execute()
                )

        except UniqueViolationError as e:
            raise ConflictErrorException(detail="User already exists", debug_detail=str(e))
        except Exception as e:
            raise ApiBaseException(status_code=500, detail="Internal Server Error", debug_detail=str(e))

    @distributed_trace()
    async def delete_user(self, user_id: UUID, model: DeleteBaseModel) -> None:
        """
        Delete user
        :param user_id:
        :return:
        """
        try:
            await (
                self._session.update(PortalUser)
                .values(is_deleted=True, delete_reason=model.reason)
                .where(PortalUser.id == user_id)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(status_code=500, detail="Internal Server Error", debug_detail=str(e))

    @distributed_trace()
    async def restore_user(self, user_ids: list[UUID]) -> None:
        """
        Restore users
        :param user_ids:
        :return:
        """
        try:
            await (
                self._session.update(PortalUser)
                .values(is_deleted=False, delete_reason=None)
                .where(PortalUser.id.in_(user_ids))
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(status_code=500, detail="Internal Server Error", debug_detail=str(e))
