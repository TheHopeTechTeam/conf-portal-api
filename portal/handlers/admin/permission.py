"""
AdminPermissionHandler
"""
import uuid
from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import ApiBaseException, ConflictErrorException
from portal.libs.consts.cache_keys import create_permission_key, CacheKeys, CacheExpiry
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalPermission, PortalVerb, PortalResource, PortalRole, PortalUser, PortalRolePermission
from portal.schemas.mixins import UUIDBaseModel
from portal.schemas.permission import PermissionBase
from portal.schemas.user import SUserSensitive
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.v1.admin.permission import (
    AdminPermissionDetail,
    AdminPermissionCreate,
    AdminPermissionUpdate,
    AdminPermissionQuery,
    AdminPermissionPageItem,
    AdminPermissionPage,
    AdminPermissionBulkAction,
    AdminPermissionList,
    AdminPermissionItem,
)


class AdminPermissionHandler:
    """AdminPermissionHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @distributed_trace()
    async def init_user_permissions_cache(self, user: SUserSensitive, expire: int) -> Optional[list[str]]:
        """
        Initialize user permissions cache
        :param user:
        :param expire:
        :return:
        """
        await self.clear_user_permissions_cache(user_id=user.id)
        permissions: Optional[list[PermissionBase]] = await self._get_user_role_permissions(user=user)
        if not permissions:
            return None
        key = create_permission_key(str(user.id))
        permission_codes = []
        for permission in permissions:
            permission_code = permission.code
            permission_codes.append(permission_code)
            await self._redis.hset(key, permission_code, permission.model_dump_json())
        await self._redis.expire(key, expire)
        return permission_codes

    @distributed_trace()
    async def clear_user_permissions_cache(self, user_id: UUID):
        """
        Clear user permissions cache
        :param user_id:
        :return:
        """
        key = create_permission_key(str(user_id))
        await self._redis.delete(key)

    @distributed_trace()
    async def _get_user_role_permissions(self, user: SUserSensitive) -> Optional[list[PermissionBase]]:
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
            .where(
                sa.or_(
                    PortalRolePermission.expire_date.is_(None),
                    PortalRolePermission.expire_date > sa.func.now()
                )
            )
            .distinct()
            .order_by(
                [
                    PortalResource.code,
                    PortalVerb.action,
                    PortalPermission.code,
                ]
            )
            .fetch(as_model=PermissionBase)
        )

    @distributed_trace()
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

    @distributed_trace()
    async def get_permission_by_id(self, permission_id: UUID) -> Optional[AdminPermissionDetail]:
        """
        Get permission by id
        :param permission_id:
        :return:
        """
        try:
            item: Optional[AdminPermissionDetail] = await (
                self._session.select(
                    PortalPermission.id,
                    PortalPermission.display_name,
                    PortalPermission.code,
                    sa.func.json_build_object(
                        sa.cast("id", sa.VARCHAR(4)), PortalResource.id,
                        sa.cast("name", sa.VARCHAR(4)), PortalResource.name,
                        sa.cast("key", sa.VARCHAR(4)), PortalResource.key,
                        sa.cast("code", sa.VARCHAR(4)), PortalResource.code
                    ).label('resource'),
                    sa.func.json_build_object(
                        sa.cast("id", sa.VARCHAR(4)), PortalVerb.id,
                        sa.cast("display_name", sa.VARCHAR(16)), PortalVerb.display_name,
                        sa.cast("action", sa.VARCHAR(8)), PortalVerb.action
                    ).label('verb'),
                    PortalPermission.is_active,
                    PortalPermission.description,
                    PortalPermission.remark
                )
                .outerjoin(PortalResource, PortalPermission.resource_id == PortalResource.id)
                .outerjoin(PortalVerb, PortalPermission.verb_id == PortalVerb.id)
                .where(PortalPermission.id == permission_id)
                .fetchrow(as_model=AdminPermissionDetail)
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return item

    @distributed_trace()
    async def get_permission_pages(
        self,
        model: AdminPermissionQuery
    ):
        """

        :param model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalPermission.id,
                PortalPermission.display_name,
                PortalPermission.code,
                PortalPermission.is_active,
                PortalPermission.description,
                PortalPermission.remark,
                PortalResource.name.label("resource_name"),
                PortalVerb.display_name.label("verb_name"),
            )
            .outerjoin(PortalResource, PortalPermission.resource_id == PortalResource.id)
            .outerjoin(PortalVerb, PortalPermission.verb_id == PortalVerb.id)
            .where(PortalPermission.is_deleted == model.deleted)
            .where(
                model.keyword, lambda: sa.or_(
                    PortalPermission.display_name.ilike(f"%{model.keyword}%"),
                    PortalPermission.code.ilike(f"%{model.keyword}%")
                )
            )
            .where(model.is_active is not None, lambda: PortalPermission.is_active == model.is_active)
            .order_by_with(
                tables=[PortalPermission],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(as_model=AdminPermissionPageItem)
        )  # type: (list[AdminPermissionPageItem], int)
        return AdminPermissionPage(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def create_permission(self, model: AdminPermissionCreate) -> UUIDBaseModel:
        """
        Create a permission
        :param model:
        :return:
        """
        permission_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalPermission)
                .values(
                    model.model_dump(exclude_none=True),
                    id=permission_id,
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Permission {model.code} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=permission_id)

    @distributed_trace()
    async def update_permission(self, permission_id: UUID, model: AdminPermissionUpdate) -> None:
        """
        Update a permission
        :param permission_id:
        :param model:
        :return:
        """
        try:
            result = await (
                self._session.update(PortalPermission)
                .values(model.model_dump())
                .where(PortalPermission.id == permission_id)
                .where(PortalPermission.is_deleted == False)
                .execute()
            )
            if result == 0:
                raise ApiBaseException(
                    status_code=404,
                    detail=f"Permission {permission_id} not found",
                )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Permission {model.code} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def delete_permission(self, permission_id: UUID, model: DeleteBaseModel) -> None:
        """
        Delete a permission
        :param permission_id:
        :param model:
        :return:
        """
        try:
            if model.permanent:
                # Hard delete - permanently remove from database
                result = await (
                    self._session.delete(PortalPermission)
                    .where(PortalPermission.id == permission_id)
                    .execute()
                )
            else:
                # Soft delete - mark as deleted with reason
                result = await (
                    self._session.update(PortalPermission)
                    .values(
                        is_deleted=True,
                        delete_reason=model.reason
                    )
                    .where(PortalPermission.id == permission_id)
                    .where(PortalPermission.is_deleted == False)
                    .execute()
                )

            if result == 0:
                raise ApiBaseException(
                    status_code=404,
                    detail=f"Permission {permission_id} not found",
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def restore_permission(self, model: AdminPermissionBulkAction) -> None:
        """
        Restore a permission
        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalPermission)
                .values(is_deleted=False, delete_reason=None)
                .where(PortalPermission.id.in_(model.ids))
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def get_permission_list(self):
        """

        :return:
        """
        cache_key = CacheKeys(resource="permission").add_attribute("list").build()
        cached = await self._redis.get(cache_key)
        if cached:
            return AdminPermissionList.model_validate_json(cached)

        permissions: list[AdminPermissionItem] = await (
            self._session.select(
                PortalPermission.id,
                PortalPermission.display_name,
                PortalPermission.code,
                PortalPermission.is_active,
                PortalPermission.description,
                PortalPermission.remark,
                PortalPermission.resource_id,
                PortalPermission.verb_id
            )
            .where(PortalPermission.is_deleted == False)
            .order_by(PortalPermission.resource_id)
            .fetch(as_model=AdminPermissionItem)
        )
        result = AdminPermissionList(items=permissions)
        await self._redis.set(cache_key, result.model_dump_json(), ex=CacheExpiry.MONTH)
        return result
