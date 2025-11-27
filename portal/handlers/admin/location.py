"""
AdminLocationHandler
"""
import uuid
from typing import Optional

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import NotFoundException, ConflictErrorException, ApiBaseException
from portal.handlers import AdminFileHandler
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalLocation
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.location import (
    AdminLocationQuery,
    AdminLocationBase,
    AdminLocationPages,
    AdminLocationDetail,
    AdminLocationCreate,
    AdminLocationUpdate, AdminLocationItem, AdminLocationList,
)


class AdminLocationHandler:
    """AdminLocationHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        file_handler: AdminFileHandler,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._file_handler = file_handler

    @distributed_trace()
    async def get_location_pages(self, model: AdminLocationQuery) -> AdminLocationPages:
        """

        :param model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalLocation.id,
                PortalLocation.name,
                PortalLocation.address,
                PortalLocation.floor,
                PortalLocation.room_number,
                PortalLocation.remark,
                PortalLocation.created_at,
                PortalLocation.updated_at
            )
            .where(PortalLocation.is_deleted == model.deleted)
            .where(
                model.keyword is not None, lambda: sa.or_(
                    PortalLocation.name.ilike(f"%{model.keyword}%"),
                    PortalLocation.address.ilike(f"%{model.keyword}%"),
                )
            )
            .where(model.room_number is not None, lambda: PortalLocation.room_number.ilike(f"%{model.room_number}%"))
            .order_by_with(
                tables=[PortalLocation],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=AdminLocationItem
            )
        )
        return AdminLocationPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def get_location_list(self) -> AdminLocationList:
        """
        Get location list
        :return:
        """
        items = await (
            self._session.select(
                PortalLocation.id,
                PortalLocation.name,
            )
            .where(PortalLocation.is_deleted == False)
            .order_by(PortalLocation.name)
            .fetch(as_model=AdminLocationBase)
        )
        return AdminLocationList(items=items)

    @distributed_trace()
    async def get_location_by_id(self, location_id: uuid.UUID) -> AdminLocationDetail:
        """

        :param location_id:
        :return:
        """
        item: Optional[AdminLocationDetail] = await (
            self._session.select(
                PortalLocation.id,
                PortalLocation.name,
                PortalLocation.address,
                PortalLocation.floor,
                PortalLocation.room_number,
                PortalLocation.latitude,
                PortalLocation.longitude,
                PortalLocation.remark,
                PortalLocation.description,
                PortalLocation.created_at,
                PortalLocation.updated_at,
            )
            .where(PortalLocation.id == location_id)
            .fetchrow(as_model=AdminLocationDetail)
        )
        if not item:
            raise NotFoundException(detail=f"Location {location_id} not found")

        item.files = await self._file_handler.get_files_by_resource_id(resource_id=item.id)
        return item

    @distributed_trace()
    async def create_location(self, model: AdminLocationCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        location_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalLocation)
                .values(
                    model.model_dump(exclude_none=True, exclude={"file_ids"}),
                    id=location_id
                )
                .execute()
            )
            await self._file_handler.update_file_association(
                file_ids=model.file_ids,
                resource_id=location_id,
                resource_name=self.__class__.__name__,
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Location {model.name} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=location_id)

    @distributed_trace()
    async def update_location(self, location_id: uuid.UUID, model: AdminLocationUpdate):
        """

        :param location_id:
        :param model:
        :return:
        """
        try:
            await (
                self._session.insert(PortalLocation)
                .values(
                    model.model_dump(exclude_none=True, exclude={"file_ids"}),
                    id=location_id
                )
                .on_conflict_do_update(
                    index_elements=[PortalLocation.id],
                    set_=model.model_dump(exclude={"file_ids"}),
                )
                .execute()
            )
            await self._file_handler.update_file_association(
                file_ids=model.file_ids,
                resource_id=location_id,
                resource_name=self.__class__.__name__,
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Location {model.name} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def delete_location(self, location_id: uuid.UUID, model: DeleteBaseModel) -> None:
        """

        :param location_id:
        :param model:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(PortalLocation)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(PortalLocation.id == location_id)
                    .execute()
                )
            else:
                await (
                    self._session.delete(PortalLocation)
                    .where(PortalLocation.id == location_id)
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def restore_locations(self, model: BulkAction) -> None:
        """

        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalLocation)
                .where(PortalLocation.id.in_(model.ids))
                .values(is_deleted=False)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
