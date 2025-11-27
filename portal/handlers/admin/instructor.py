"""
AdminInstructorHandler
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
from portal.models import PortalInstructor
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.admin.instructor import (
    AdminInstructorQuery,
    AdminInstructorBase,
    AdminInstructorPages,
    AdminInstructorDetail,
    AdminInstructorCreate,
    AdminInstructorUpdate, AdminInstructorList,
)


class AdminInstructorHandler:
    """AdminInstructorHandler"""

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
    async def get_instructor_pages(self, model: AdminInstructorQuery) -> AdminInstructorPages:
        """

        :param model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalInstructor.id,
                PortalInstructor.name,
                PortalInstructor.title,
                PortalInstructor.bio,
                PortalInstructor.remark,
                PortalInstructor.created_at,
                PortalInstructor.updated_at,
            )
            .where(PortalInstructor.is_deleted == model.deleted)
            .where(
                model.keyword is not None, lambda: sa.or_(
                    PortalInstructor.name.ilike(f"%{model.keyword}%"),
                    PortalInstructor.title.ilike(f"%{model.keyword}%"),
                    PortalInstructor.bio.ilike(f"%{model.keyword}%"),
                )
            )
            .order_by_with(
                tables=[PortalInstructor],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=AdminInstructorBase
            )
        )
        return AdminInstructorPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def get_instructor_list(self) -> AdminInstructorList:
        """

        :return:
        """
        items = await (
            self._session.select(
                PortalInstructor.id,
                PortalInstructor.name,
                PortalInstructor.title,
                PortalInstructor.bio,
                PortalInstructor.remark,
                PortalInstructor.created_at,
                PortalInstructor.updated_at,
            )
            .where(PortalInstructor.is_deleted == False)
            .order_by(PortalInstructor.created_at.desc())
            .fetch(as_model=AdminInstructorBase)
        )
        return AdminInstructorList(items=items)

    @distributed_trace()
    async def get_instructor_by_id(self, instructor_id: uuid.UUID) -> AdminInstructorDetail:
        """

        :param instructor_id:
        :return:
        """
        item: Optional[AdminInstructorDetail] = await (
            self._session.select(
                PortalInstructor.id,
                PortalInstructor.name,
                PortalInstructor.title,
                PortalInstructor.bio,
                PortalInstructor.remark,
                PortalInstructor.description,
                PortalInstructor.created_at,
                PortalInstructor.updated_at,
            )
            .where(PortalInstructor.id == instructor_id)
            .fetchrow(as_model=AdminInstructorDetail)
        )
        if not item:
            raise NotFoundException(detail=f"Instructor {instructor_id} not found")

        item.files = await self._file_handler.get_files_by_resource_id(resource_id=item.id)
        return item

    @distributed_trace()
    async def create_instructor(self, model: AdminInstructorCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        instructor_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalInstructor)
                .values(
                    model.model_dump(exclude_none=True, exclude={"file_ids"}),
                    id=instructor_id
                )
                .execute()
            )
            await self._file_handler.update_file_association(
                file_ids=model.file_ids,
                resource_id=instructor_id,
                resource_name=self.__class__.__name__,
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Instructor {model.name} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=instructor_id)

    @distributed_trace()
    async def update_instructor(self, instructor_id: uuid.UUID, model: AdminInstructorUpdate):
        """

        :param instructor_id:
        :param model:
        :return:
        """
        try:
            await (
                self._session.insert(PortalInstructor)
                .values(
                    model.model_dump(exclude_none=True, exclude={"file_ids"}),
                    id=instructor_id
                )
                .on_conflict_do_update(
                    index_elements=[PortalInstructor.id],
                    set_=model.model_dump(exclude={"file_ids"}),
                )
                .execute()
            )
            await self._file_handler.update_file_association(
                file_ids=model.file_ids,
                resource_id=instructor_id,
                resource_name=self.__class__.__name__,
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"Instructor {model.name} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def delete_instructor(self, instructor_id: uuid.UUID, model: DeleteBaseModel) -> None:
        """

        :param instructor_id:
        :param model:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(PortalInstructor)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(PortalInstructor.id == instructor_id)
                    .execute()
                )
            else:
                await (
                    self._session.delete(PortalInstructor)
                    .where(PortalInstructor.id == instructor_id)
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def restore_instructors(self, model: BulkAction) -> None:
        """

        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalInstructor)
                .where(PortalInstructor.id.in_(model.ids))
                .values(is_deleted=False)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

