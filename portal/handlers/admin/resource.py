"""
Handler for admin resource
"""
import asyncio
import uuid

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from redis.asyncio import Redis
from sqlalchemy.orm import aliased

from portal.config import settings
from portal.exceptions.responses import ApiBaseException, ConflictErrorException, UnauthorizedException, NotFoundException
from portal.libs.contexts.user_context import UserContext, get_user_context
from portal.libs.database import Session, RedisPool
from portal.models import PortalResource, PortalPermission, PortalRole, PortalUser, PortalRolePermission
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import DeleteQueryBaseModel
from portal.serializers.v1.admin.resource import (
    ResourceCreate,
    ResourceUpdate,
    ResourceChangeSequence,
    ResourceItem,
    ResourceTree,
    ResourceTreeItem,
    ResourceList, ResourceDetail, ResourceChangeParent,
)


class AdminResourceHandler:
    """AdminResourceHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._user_ctx: UserContext = get_user_context()

    async def get_resource(self, resource_id: uuid.UUID) -> ResourceDetail:
        """

        :param resource_id:
        :return:
        """
        pr_parent = aliased(PortalResource)
        resource: ResourceDetail = await (
            self._session.select(
                PortalResource.id,
                PortalResource.name,
                PortalResource.key,
                PortalResource.code,
                PortalResource.icon,
                PortalResource.path,
                PortalResource.type,
                PortalResource.remark,
                PortalResource.description,
                PortalResource.sequence,
                PortalResource.is_deleted,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(4)), pr_parent.id,
                    sa.cast("name", sa.VARCHAR(4)), pr_parent.name,
                    sa.cast("key", sa.VARCHAR(4)), pr_parent.key,
                    sa.cast("code", sa.VARCHAR(4)), pr_parent.code,
                    sa.cast("icon", sa.VARCHAR(4)), pr_parent.icon,
                ).label("parent")
            )
            .select_from(PortalResource)
            .outerjoin(pr_parent, PortalResource.pid == pr_parent.id)
            .where(PortalResource.id == resource_id)
            .fetchrow(as_model=ResourceDetail)
        )
        if not resource:
            raise NotFoundException(detail=f"Resource {resource_id} not found")
        return resource

    async def create_resource(self, model: ResourceCreate) -> UUIDBaseModel:
        """
        Create a resource
        TODO: Log action
        :param model:
        :return:
        """
        rid = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalResource)
                .values(
                    model.model_dump(exclude_none=True),
                    id=rid,
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Resource {model.code} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=rid)

    async def change_parent(self, resource_id: uuid.UUID, model: ResourceChangeParent):
        """

        :param resource_id:
        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalResource)
                .values(pid=model.pid)
                .where(PortalResource.id == resource_id)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    async def update_resource(self, resource_id: uuid.UUID, model: ResourceUpdate):
        """
        Update a resource
        TODO: Log action
        :param resource_id:
        :param model:
        :return:
        """
        try:
            result = await (
                self._session.update(PortalResource)
                .values(model.model_dump())
                .where(PortalResource.id == resource_id)
                .execute()
            )
            if result == 0:
                raise ApiBaseException(
                    status_code=404,
                    detail=f"Resource {resource_id} not found",
                )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Resource {model.code} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    async def change_sequence(self, model: ResourceChangeSequence):
        """

        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalResource)
                .values(sequence=model.another_sequence)
                .where(PortalResource.id == model.id)
                .execute()
            )
            await (
                self._session.update(PortalResource)
                .values(sequence=model.sequence)
                .where(PortalResource.id == model.another_id)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    async def delete_resource(self, resource_id: uuid.UUID, model: DeleteBaseModel):
        """
        Delete a resource or soft delete. If permanent is True, then delete permanently.
        If resource_id is a parent resource, then all its children will be deleted as well.
        TODO: Log action
        :param resource_id:
        :param model:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(PortalResource)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(sa.or_(PortalResource.id == resource_id, PortalResource.pid == resource_id))
                    .execute()
                )
            else:
                await self._session.delete(PortalResource).where(PortalResource.id == resource_id).execute()
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    async def restore_resource(self, resource_id: uuid.UUID):
        """
        Restore the resource by setting is_deleted to False and deleted_reason to None.
        If resource_id is a parent resource, then all its children will be restored as well.
        TODO: Log action
        :param resource_id:
        :return:
        """
        try:
            await (
                self._session.update(PortalResource)
                .values(is_deleted=False, delete_reason=None)
                .where(sa.or_(PortalResource.id == resource_id, PortalResource.pid == resource_id))
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @staticmethod
    def build_tree(items: list[ResourceItem]) -> list[ResourceTreeItem]:
        """
        Build a tree from flat resource items using id/pid relations.
        Returns a list of root nodes, each with recursive children.
        :param items:
        :return:
        """
        nodes = {item.id: ResourceTreeItem(**item.model_dump()) for item in items}
        root_items: list[ResourceTreeItem] = []
        for node in nodes.values():
            if node.pid and node.pid in nodes:
                if not nodes[node.pid].children:
                    nodes[node.pid].children = []
                nodes[node.pid].children.append(node)
            else:
                root_items.append(node)

        def sort_nodes(arr: list[ResourceTreeItem]) -> None:
            arr.sort(key=lambda n: (n.sequence, n.name))
            for n in arr:
                if n.children:
                    sort_nodes(n.children)

        sort_nodes(root_items)
        return root_items

    async def get_admin_resource_tree(self) -> ResourceTree:
        """

        :return:
        """
        if not self._user_ctx.user_id or (not self._user_ctx.is_superuser and not self._user_ctx.is_admin):
            raise UnauthorizedException()

        resources: list[ResourceItem] = await self.get_resource_menus()
        hierarchical_items = self.build_tree(resources)
        return ResourceTree(items=hierarchical_items)

    async def get_resource_menus(self, is_deleted: bool = False) -> list[ResourceItem]:
        """

        :param is_deleted:
        :return:
        """
        resources: list[ResourceItem] = await (
            self._session.select(
                PortalResource.id,
                PortalResource.pid,
                PortalResource.name,
                PortalResource.key,
                PortalResource.code,
                PortalResource.icon,
                PortalResource.path,
                PortalResource.type,
                PortalResource.description,
                PortalResource.sequence,
                PortalResource.is_deleted
            )
            .where(
                is_deleted == True, lambda: sa.or_(
                    PortalResource.is_deleted == is_deleted,
                    sa.and_(PortalResource.pid.is_(None), PortalResource.is_deleted == False)
                )
                )
            .where(is_deleted == False, lambda: PortalResource.is_deleted == is_deleted)
            .order_by(PortalResource.sequence)
            .fetch(as_model=ResourceItem)
        )
        return resources

    async def get_resource_by_user_id(self, user_id: uuid.UUID) -> list[ResourceItem]:
        """

        :param user_id:
        :return:
        """
        user_resources_subquery = (
            self._session.select(
                PortalResource.id.label("resource_id"),
                PortalResource.pid.label("parent_id")
            )
            .select_from(PortalUser)
            .join(PortalUser.roles)
            .outerjoin(PortalRolePermission, PortalRolePermission.role_id == PortalRole.id)
            .outerjoin(PortalPermission, PortalPermission.id == PortalRolePermission.permission_id)
            .outerjoin(PortalResource, PortalPermission.resource_id == PortalResource.id)
            .where(PortalUser.id == user_id)
            .where(PortalResource.is_deleted == False)
            .where(PortalResource.is_visible == True)
            .where(PortalPermission.is_active == True)
            .where(PortalPermission.is_deleted == False)
            .where(PortalRole.is_active == True)
            .where(PortalRole.is_deleted == False)
            .where(sa.or_(PortalRolePermission.expire_date.is_(None), PortalRolePermission.expire_date > sa.func.now()))
            .subquery()
        )

        # 查询资源：资源 ID 在子查询中，或者资源 ID 是子查询中某个资源的父 ID
        resources: list[ResourceItem] = await (
            self._session.select(
                PortalResource.id,
                PortalResource.pid,
                PortalResource.name,
                PortalResource.key,
                PortalResource.code,
                PortalResource.icon,
                PortalResource.path,
                PortalResource.type,
                PortalResource.description,
                PortalResource.sequence,
                PortalResource.is_deleted
            )
            .where(
                sa.or_(
                    PortalResource.id.in_(
                        sa.select(user_resources_subquery.c.resource_id)
                    ),
                    PortalResource.id.in_(
                        sa.select(user_resources_subquery.c.parent_id)
                        .where(user_resources_subquery.c.parent_id.isnot(None))
                    )
                )
            )
            .where(PortalResource.is_deleted == False)
            .distinct()
            .order_by(PortalResource.sequence)
            .fetch(as_model=ResourceItem)
        )
        return resources

    async def get_resources(self, model: DeleteQueryBaseModel):
        """
        get resources
        :param model:
        :return:
        """
        if not self._user_ctx.user_id or not self._user_ctx.is_admin:
            raise UnauthorizedException()
        resources = await self.get_resource_menus(is_deleted=model.deleted)
        return ResourceList(items=resources)

    async def get_user_permission_menus(self) -> ResourceList:
        """

        :return:
        """
        if not self._user_ctx.user_id or not self._user_ctx.is_admin:
            raise UnauthorizedException()

        if self._user_ctx.is_superuser:
            resource_items = await self.get_resource_menus()
        else:
            resource_items = await self.get_resource_by_user_id(user_id=self._user_ctx.user_id)

        await asyncio.sleep(1)
        return ResourceList(items=resource_items)
