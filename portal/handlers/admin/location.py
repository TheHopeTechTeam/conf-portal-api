"""
AdminLocationHandler
"""
import uuid
from typing import Optional

from asyncpg import UniqueViolationError
from redis.asyncio import Redis

import sqlalchemy as sa
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
    LocationQuery,
    LocationBase,
    LocationPages,
    LocationDetail,
    LocationCreate,
    LocationUpdate,
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

    async def get_location_pages(self, model: LocationQuery):
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
                PortalLocation.updated_at,
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
                as_model=LocationBase
            )
        )
        return LocationPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    async def get_location_by_id(self, location_id: uuid.UUID) -> LocationDetail:
        """

        :param location_id:
        :return:
        """
        item: Optional[LocationDetail] = await (
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
            .where(PortalLocation.is_deleted == False)
            .fetchrow(as_model=LocationDetail)
        )
        if not item:
            raise NotFoundException(detail=f"Location {location_id} not found")

        item.image_urls = await self._file_handler.get_signed_url_by_resource_id(resource_id=item.id)
        return item

    async def create_location(self, model: LocationCreate) -> UUIDBaseModel:
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
            # TODO: create relation between location and files
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Location {model.name} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
            )
        else:
            return UUIDBaseModel(id=location_id)

    @distributed_trace()
    async def update_location(self, location_id: uuid.UUID, model: LocationUpdate):
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

        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Location {model.name} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
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
                    .where(PortalLocation.id == location_id)
                    .values(is_deleted=True)
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

