"""
Handler for admin resource
"""
import uuid

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import ApiBaseException, ResourceExistsException, UnauthorizedException
from portal.libs.contexts.user_context import UserContext, get_user_context
from portal.libs.database import Session, RedisPool
from portal.models import PortalResource, PortalPermission, PortalRole, PortalUser, PortalRolePermission
from portal.serializers.mixins import GenericQueryBaseModel
from portal.serializers.v1.admin.resource import ResourceCreate, ResourceUpdate, ResourceChangeSequence, ResourceItem, ResourceTree, ResourceTreeItem


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

    async def get_resources(self, query: GenericQueryBaseModel):
        """

        :param query:
        :return:
        """

    async def create_resource(self, model: ResourceCreate):
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
            raise ResourceExistsException(
                detail=f"Resource {model.code} already exists",
                debug_detail=str(e),
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
            raise ResourceExistsException(
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

    async def delete_resource(self, resource_id: uuid.UUID, delete_reason: str = None, permanent: bool = False):
        """
        Delete a resource or soft delete. If permanent is True, then delete permanently.
        If resource_id is a parent resource, then all its children will be deleted as well.
        TODO: Log action
        :param resource_id:
        :param delete_reason:
        :param permanent:
        :return:
        """
        try:
            if not permanent:
                await (
                    self._session.update(PortalResource)
                    .values(is_deleted=True, deleted_reason=delete_reason)
                    .where(sa.and_(PortalResource.id == resource_id, PortalResource.pid == resource_id))
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
                .values(is_deleted=False, deleted_reason=None)
                .where(sa.and_(PortalResource.id == resource_id, PortalResource.pid == resource_id))
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
                PortalResource.sequence
            )
            .where(PortalResource.is_deleted == is_deleted)
            .order_by(PortalResource.sequence)
            .fetch(as_model=ResourceItem)
        )
        return resources

    async def get_resource_by_user_id(self, user_id: uuid.UUID) -> list[ResourceItem]:
        """

        :param user_id:
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
                PortalResource.sequence
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
            .order_by(PortalResource.sequence)
            .fetch(as_model=ResourceItem)
        )
        return resources

    async def get_user_permission_menus(self):
        """

        :return:
        """
        if not self._user_ctx.user_id or not self._user_ctx.is_admin:
            raise UnauthorizedException()

        if self._user_ctx.is_superuser:
            return await self.get_resource_menus()
        else:
            return await self.get_resource_by_user_id(user_id=self._user_ctx.user_id)
