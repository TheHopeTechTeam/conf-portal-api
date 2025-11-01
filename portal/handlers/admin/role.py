"""
AdminRoleHandler
"""
import uuid
from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from asyncpg import UniqueViolationError
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import ConflictErrorException, ApiBaseException
from portal.libs.consts.cache_keys import create_user_role_key
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.models import PortalRole, PortalUser, PortalPermission, PortalResource, PortalRolePermission
from portal.schemas.mixins import UUIDBaseModel
from portal.schemas.user import SUserSensitive
from portal.serializers.mixins import GenericQueryBaseModel, DeleteBaseModel
from portal.serializers.v1.admin.role import RolePages, RoleTableItem, RoleCreate, RoleUpdate, RolePermissionAssign


class AdminRoleHandler:
    """AdminRoleHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    async def init_user_roles_cache(self, user: SUserSensitive, expire: int) -> Optional[list[str]]:
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

    async def get_role_pages(self, model: GenericQueryBaseModel) -> RolePages:
        """

        :param model:
        :return:
        """
        permissions_jsonb = sa.cast(
            sa.func.json_build_object(
                sa.cast("id", sa.VARCHAR(4)), PortalPermission.id,
                sa.cast("resource_name", sa.VARCHAR(16)), PortalResource.name,
                sa.cast("display_name", sa.VARCHAR(16)), PortalPermission.display_name,
                sa.cast("code", sa.VARCHAR(4)), PortalPermission.code,
            ),
            JSONB,
        )
        agg_permissions = sa.func.array_agg(
            sa.distinct(permissions_jsonb)
        ).filter(PortalPermission.id.isnot(None))

        permissions_coalesced = sa.func.coalesce(
            agg_permissions,
            sa.cast(sa.text("'{}'"), ARRAY(JSONB))
        ).label("permissions")

        items, count = await (
            self._session.select(
                PortalRole.id,
                PortalRole.code,
                PortalRole.name,
                PortalRole.is_active,
                PortalRole.created_at,
                PortalRole.created_by,
                PortalRole.updated_at,
                PortalRole.updated_by,
                PortalRole.delete_reason,
                PortalRole.description,
                PortalRole.remark,
                permissions_coalesced
            )
            .select_from(PortalRole)
            .outerjoin(PortalRolePermission, PortalRolePermission.role_id == PortalRole.id)
            .outerjoin(PortalPermission, PortalPermission.id == PortalRolePermission.permission_id)
            .outerjoin(PortalResource, PortalPermission.resource_id == PortalResource.id)
            .where(PortalRole.is_deleted == model.deleted)
            .where(
                model.keyword, lambda: sa.or_(
                    PortalRole.name.ilike(f"%{model.keyword}%"),
                    PortalRole.code.ilike(f"%{model.keyword}%")
                )
            )
            .group_by(PortalRole.id)
            .order_by_with(
                tables=[PortalRole],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=RoleTableItem
            )
        )  # type: (list[RoleTableItem], int)

        return RolePages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def get_role_by_id(self, role_id: UUID) -> Optional[RoleTableItem]:
        """

        :param role_id:
        :return:
        """
        permissions_jsonb = sa.cast(
            sa.func.json_build_object(
                sa.cast("id", sa.VARCHAR(4)), PortalPermission.id,
                sa.cast("resource_name", sa.VARCHAR(16)), PortalResource.name,
                sa.cast("display_name", sa.VARCHAR(16)), PortalPermission.display_name,
                sa.cast("code", sa.VARCHAR(4)), PortalPermission.code,
            ),
            JSONB,
        )
        agg_permissions = sa.func.array_agg(
            sa.distinct(permissions_jsonb)
        ).filter(PortalPermission.id.isnot(None))

        permissions_coalesced = sa.func.coalesce(
            agg_permissions,
            sa.cast(sa.text("'{}'"), ARRAY(JSONB))
        ).label("permissions")
        role: Optional[RoleTableItem] = await (
            self._session.select(
                PortalRole.id,
                PortalRole.code,
                PortalRole.name,
                PortalRole.is_active,
                PortalRole.created_at,
                PortalRole.created_by,
                PortalRole.updated_at,
                PortalRole.updated_by,
                PortalRole.delete_reason,
                PortalRole.description,
                PortalRole.remark,
                permissions_coalesced
            )
            .select_from(PortalRole)
            .outerjoin(PortalRolePermission, PortalRolePermission.role_id == PortalRole.id)
            .outerjoin(PortalPermission, PortalPermission.id == PortalRolePermission.permission_id)
            .outerjoin(PortalResource, PortalPermission.resource_id == PortalResource.id)
            .where(PortalRole.id == role_id)
            .group_by(PortalRole.id)
            .fetchrow(as_model=RoleTableItem)
        )
        if not role:
            return None
        return role

    @distributed_trace()
    async def create_role(self, model: RoleCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        role_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalRole)
                .values(
                    model.model_dump(exclude_none=True, exclude={"permissions"}),
                    id=role_id,
                )
                .execute()
            )
            await (
                self._session.insert(PortalRolePermission)
                .values(
                    [
                        {"role_id": role_id.hex, "permission_id": permission_id.hex}
                        for permission_id in model.permissions
                    ]
                )
                .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail="Role code already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=role_id)

    @distributed_trace()
    async def update_role(self, role_id: UUID, model: RoleUpdate) -> None:
        """

        :param role_id:
        :param model:
        :return:
        """
        try:
            result = await (
                self._session.insert(PortalRole)
                .values(
                    model.model_dump(exclude_none=True, exclude={"permissions"}),
                    id=role_id,
                )
                .on_conflict_do_update(
                    index_elements=[PortalRole.id],
                    set_=model.model_dump(exclude={"permissions"}),
                )
                .execute()
            )

            permission_ids: list[UUID] = await (
                self._session.select(PortalRolePermission.permission_id)
                .where(PortalRolePermission.role_id == role_id)
                .fetchvals()
            )
            delete_permission_ids = []
            insert_permission_ids = []
            for permission_id in model.permissions:
                if permission_id not in permission_ids:
                    insert_permission_ids.append(permission_id)
                if permission_id in permission_ids:
                    delete_permission_ids.append(permission_id)

            if insert_permission_ids:
                await (
                    self._session.insert(PortalRolePermission)
                    .values(
                        [
                            {"role_id": role_id.hex, "permission_id": permission_id.hex}
                            for permission_id in insert_permission_ids
                        ]
                    )
                    .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
                    .execute()
                )

            if delete_permission_ids:
                await (
                    self._session.delete(PortalRolePermission)
                    .where(PortalRolePermission.role_id == role_id)
                    .where(PortalRolePermission.permission_id.in_(delete_permission_ids))
                )

            if result == 0:
                raise ApiBaseException(
                    status_code=404,
                    detail=f"Role {role_id} not found",
                )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail="Role code already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def delete_role(self, role_id: UUID, model: DeleteBaseModel) -> None:
        """

        :param model:
        :param role_id:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(PortalRole)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(PortalRole.id == role_id)
                    .execute()
                )
            else:
                await (
                    self._session.delete(PortalRolePermission)
                    .where(PortalRolePermission.role_id == role_id)
                    .execute()
                )
                await (
                    self._session.delete(PortalRole)
                    .where(PortalRole.id == role_id)
                    .execute()
                )

        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def restore_role(self, role_id: UUID) -> None:
        """

        :param role_id:
        :return:
        """
        try:
            await (
                self._session.update(PortalRole)
                .values(is_deleted=False, delete_reason=None)
                .where(PortalRole.id == role_id)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def assign_role_permissions(self, role_id: UUID, model: RolePermissionAssign) -> None:
        """

        :param role_id:
        :param model:
        :return:
        """
        original_permissions = await (
            self._session.select(PortalRolePermission.permission_id)
            .where(PortalRolePermission.role_id == role_id)
            .fetchvals()
        )
        insert_permissions = [
            {
                "role_id": role_id,
                "permission_id": permission_id
            } for permission_id in model.permission_ids if permission_id not in original_permissions
        ]
        delete_permissions = [
            permission_id for permission_id in original_permissions if permission_id not in model.permission_ids
        ]
        try:
            await (
                self._session.insert(PortalRolePermission)
                .values(insert_permissions)
                .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
                .execute()
            )
            await (
                self._session.delete(PortalRolePermission)
                .where(PortalRolePermission.role_id == role_id)
                .where(PortalRolePermission.permission_id.in_(delete_permissions))
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
