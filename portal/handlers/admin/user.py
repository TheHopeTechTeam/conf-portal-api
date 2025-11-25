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
from portal.libs.contexts.user_context import UserContext, get_user_context
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalUser, PortalUserProfile, PortalUserRole
from portal.providers.password_provider import PasswordProvider
from portal.schemas.mixins import UUIDBaseModel
from portal.schemas.user import SUserSensitive
from portal.serializers.mixins.base import DeleteBaseModel
from portal.serializers.v1.admin.user import (
    UserCreate,
    UserTableItem,
    UserPages,
    UserUpdate,
    UserItem,
    UserQuery,
    UserBulkAction,
    ChangePassword,
    BindRole,
    UserRoles, UserBase, UserList,
)


class AdminUserHandler:
    """AdminUserHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        password_provider: PasswordProvider,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._password_provider = password_provider
        self._user_ctx: Optional[UserContext] = get_user_context()

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
    async def get_user_list(self, keyword: Optional[str] = None) -> UserList:
        """
        Get user list
        :param keyword:
        :return:
        """
        users: list[UserBase] = await (
            self._session.select(
                PortalUser.id,
                PortalUser.phone_number,
                PortalUser.email,
                PortalUserProfile.display_name,
            )
            .join(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(
                keyword, lambda: sa.or_(
                    PortalUser.phone_number.ilike(f"%{keyword}%"),
                    PortalUser.email.ilike(f"%{keyword}%"),
                    PortalUserProfile.display_name.ilike(f"%{keyword}%")
                )
            )
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .order_by(PortalUser.created_at.asc())
            .limit(100)
            .fetch(as_model=UserBase)
        )
        return UserList(items=users)

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
    async def get_current_user(self) -> Optional[UserItem]:
        """

        :return:
        """
        if not self._user_ctx:
            return None
        return await self.get_user_by_id(self._user_ctx.user_id)

    @distributed_trace()
    async def create_user(self, model: UserCreate) -> UUIDBaseModel:
        """
        Create user
        :param model:
        :return:
        """
        if model.password != model.password_confirm:
            raise ApiBaseException(status_code=400, detail="Passwords do not match")
        user_id = uuid.uuid4()
        try:
            if not self._password_provider.validate_password(model.password):
                raise ApiBaseException(
                    status_code=400,
                    detail="Password is not valid."
                )
            # Hash password
            password_hash = self._password_provider.hash_password(model.password)
            # Create PortalUser
            user_fields = {
                "id": user_id,
                "phone_number": model.phone_number,
                "email": model.email,
                "password_hash": password_hash,
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
    async def update_current_user(self, model: UserUpdate) -> None:
        """
        Update current user
        :param model:
        :return:
        """
        if not self._user_ctx:
            raise ApiBaseException(status_code=403, detail="Forbidden")
        try:
            user_fields = {
                "phone_number": model.phone_number,
                "email": model.email,
                "remark": model.remark,
            }

            if user_fields:
                result = await (
                    self._session.update(PortalUser)
                    .values(**user_fields, updated_at=sa.func.now())
                    .where(PortalUser.id == self._user_ctx.user_id)
                    .execute()
                )
                if result == 0:
                    raise ApiBaseException(status_code=404, detail="User not found")

            # Update PortalUserProfile
            profile_fields = {
                "display_name": model.display_name,
                "gender": model.gender,
            }

            if profile_fields:
                await (
                    self._session.update(PortalUserProfile)
                    .values(**profile_fields, updated_at=sa.func.now())
                    .where(PortalUserProfile.user_id == self._user_ctx.user_id)
                    .execute()
                )
        except UniqueViolationError as e:
            raise ConflictErrorException(detail="User already exists", debug_detail=str(e))
        except Exception as e:
            raise ApiBaseException(status_code=500, detail="Internal Server Error", debug_detail=str(e))

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
        :param model:
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
    async def restore_user(self, model: UserBulkAction) -> None:
        """
        Restore users
        :param model:
        :return:
        """
        if not model.ids:
            raise ApiBaseException(status_code=400, detail="No user ids provided")
        ids = [_id.hex for _id in model.ids]
        try:
            await (
                self._session.update(PortalUser)
                .values(is_deleted=False, delete_reason=None)
                .where(PortalUser.id.in_(ids))
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(status_code=500, detail="Internal Server Error", debug_detail=str(e))

    @distributed_trace()
    async def get_user_roles(self, user_id: UUID) -> UserRoles:
        """

        :param user_id:
        :return:
        """
        roles: list[UUID] = await (
            self._session.select(PortalUserRole.role_id)
            .where(PortalUserRole.user_id == user_id)
            .fetchvals()
        )
        return UserRoles(role_ids=roles)

    @distributed_trace()
    async def bind_roles(self, user_id: UUID, model: BindRole) -> None:
        """

        :param user_id:
        :param model:
        :return:
        """
        original_roles = await (
            self._session.select(PortalUserRole.role_id)
            .where(PortalUserRole.user_id == user_id)
            .fetchvals()
        )
        new_role_ids = set(model.role_ids or [])
        old_role_ids = set(original_roles)
        insert_role_ids = list(new_role_ids - old_role_ids)
        delete_role_ids = list(old_role_ids - new_role_ids)

        try:
            if insert_role_ids:
                await (
                    self._session.insert(PortalUserRole)
                    .values(
                        [
                            {"user_id": user_id, "role_id": role_id} for role_id in insert_role_ids
                        ]
                    )
                    .on_conflict_do_nothing(index_elements=["user_id", "role_id"])
                    .execute()
                )
            if delete_role_ids:
                await (
                    self._session.delete(PortalUserRole)
                    .where(PortalUserRole.user_id == user_id)
                    .where(PortalUserRole.role_id.in_(delete_role_ids))
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(status_code=500, detail="Internal Server Error", debug_detail=str(e))

    @distributed_trace()
    async def change_password(self, user_id: UUID, model: ChangePassword) -> None:
        """

        :param user_id:
        :param model:
        :return:
        """
        user: Optional[SUserSensitive] = await self.get_user_detail_by_id(user_id)
        if not user:
            raise ApiBaseException(status_code=404, detail="User not found")
        if user.id != self._user_ctx.user_id:
            raise ApiBaseException(status_code=403, detail="Forbidden")
        if not self._password_provider.verify_password(model.old_password, user.password_hash):
            raise ApiBaseException(status_code=400, detail="Old password is not valid")
        if model.new_password != model.new_password_confirm:
            raise ApiBaseException(status_code=400, detail="New passwords do not match")
        if not self._password_provider.validate_password(model.new_password):
            raise ApiBaseException(status_code=400, detail="New password is not valid")
        password_hash = self._password_provider.hash_password(model.new_password)
        await (
            self._session.update(PortalUser)
            .values(
                password_hash=password_hash,
                updated_at=sa.func.now(),
                password_changed_at=sa.func.now()
            )
            .where(PortalUser.id == user_id)
            .execute()
        )
        return None

    @distributed_trace()
    async def reset_password(self, user_id: UUID, new_password: str) -> None:
        """

        :param user_id:
        :param new_password:
        :return:
        """
        password_hash = self._password_provider.hash_password(new_password)
        await (
            self._session.update(PortalUser)
            .values(
                password_hash=password_hash,
                password_changed_at=sa.func.now(),
                updated_at=sa.func.now()
            )
            .where(PortalUser.id == user_id)
            .execute()
        )
