"""
AdminFaqHandler
"""
import uuid
from typing import Optional

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import NotFoundException, ConflictErrorException, ApiBaseException, BadRequestException
from portal.handlers.admin.log import AdminLogHandler
from portal.libs.consts.enums import OperationType
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalFaq, PortalFaqCategory
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction, DeleteQueryBaseModel
from portal.serializers.v1.admin.faq import (
    AdminFaqQuery,
    AdminFaqPages,
    AdminFaqDetail,
    AdminFaqCreate,
    AdminFaqUpdate,
    AdminFaqCategoryBase,
    AdminFaqCategoryItem,
    AdminFaqCategoryList,
    AdminFaqCategoryDetail,
    AdminFaqCategoryCreate,
    AdminFaqCategoryUpdate,
    AdminFaqItem,
    AdminFaqSequenceItem,
    AdminFaqCategoryChangeSequence,
    AdminFaqChangeSequence,
)


class AdminFaqHandler:
    """AdminFaqHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
        log_handler: AdminLogHandler,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._log_handler = log_handler

    def _faq_pages_base_query(self, model: AdminFaqQuery):
        """

        :param model:
        :return:
        """
        return (
            self._session.select(
                PortalFaq.id,
                PortalFaq.category_id,
                PortalFaqCategory.name.label("category_name"),
                PortalFaq.question,
                PortalFaq.related_link,
                PortalFaq.remark,
                PortalFaq.sequence,
                PortalFaq.created_at,
                PortalFaq.updated_at,
            )
            .outerjoin(PortalFaqCategory, PortalFaq.category_id == PortalFaqCategory.id)
            .where(PortalFaq.is_deleted == model.deleted)
            .where(
                model.keyword is not None, lambda: sa.or_(
                    PortalFaq.question.ilike(f"%{model.keyword}%"),
                    PortalFaq.answer.ilike(f"%{model.keyword}%"),
                )
            )
            .where(model.category_id is not None, lambda: PortalFaq.category_id == model.category_id)
        )

    def _apply_faq_pages_order(self, query, model: AdminFaqQuery):
        """

        :param query:
        :param model:
        :return:
        """
        if model.order_by:
            return query.order_by_with(
                tables=[PortalFaqCategory, PortalFaq],
                order_by=model.order_by,
                descending=model.descending or False
            )
        return query.order_by(
            [
                PortalFaqCategory.sequence.asc(),
                PortalFaq.sequence.asc(),
                PortalFaq.id.asc(),
            ],
        )

    @distributed_trace()
    async def get_faq_pages(self, model: AdminFaqQuery) -> AdminFaqPages:
        """

        :param model:
        :return:
        """
        ordered_query = self._apply_faq_pages_order(self._faq_pages_base_query(model), model)
        items, count = await (
            ordered_query
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=AdminFaqItem
            )
        )

        sequence_neighbor_query = self._apply_faq_pages_order(
            (
                self._session.select(
                    PortalFaq.id,
                    PortalFaq.sequence,
                    PortalFaq.category_id,
                )
                .outerjoin(PortalFaqCategory, PortalFaq.category_id == PortalFaqCategory.id)
                .where(PortalFaq.is_deleted == model.deleted)
                .where(
                    model.keyword is not None, lambda: sa.or_(
                        PortalFaq.question.ilike(f"%{model.keyword}%"),
                        PortalFaq.answer.ilike(f"%{model.keyword}%"),
                    )
                )
                .where(model.category_id is not None, lambda: PortalFaq.category_id == model.category_id)
            ),
            model,
        )

        prev_item: Optional[AdminFaqSequenceItem] = None
        if model.page > 0 and count > 0:
            prev_item = await (
                sequence_neighbor_query
                .offset(model.page * model.page_size - 1)
                .limit(1)
                .fetchrow(as_model=AdminFaqSequenceItem)
            )

        next_item: Optional[AdminFaqSequenceItem] = None
        if count > (model.page + 1) * model.page_size:
            next_item = await (
                sequence_neighbor_query
                .offset((model.page + 1) * model.page_size)
                .limit(1)
                .fetchrow(as_model=AdminFaqSequenceItem)
            )

        return AdminFaqPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items,
            prev_item=prev_item,
            next_item=next_item,
        )

    @distributed_trace()
    async def get_faq_by_id(self, faq_id: uuid.UUID) -> AdminFaqDetail:
        """

        :param faq_id:
        :return:
        """
        item: Optional[AdminFaqDetail] = await (
            self._session.select(
                PortalFaq.id,
                PortalFaq.question,
                PortalFaq.answer,
                PortalFaq.related_link,
                PortalFaq.remark,
                PortalFaq.description,
                PortalFaq.created_at,
                PortalFaq.updated_at,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalFaqCategory.id, sa.String),
                    sa.cast("name", sa.VARCHAR(255)), PortalFaqCategory.name,
                ).label("category"),
            )
            .outerjoin(PortalFaqCategory, PortalFaq.category_id == PortalFaqCategory.id)
            .where(PortalFaq.id == faq_id)
            .where(PortalFaq.is_deleted == False)
            .fetchrow(as_model=AdminFaqDetail)
        )
        if not item:
            raise NotFoundException(detail=f"FAQ {faq_id} not found")

        return item

    @distributed_trace()
    async def create_faq(self, model: AdminFaqCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        faq_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalFaq)
                .values(
                    model.model_dump(exclude_none=True),
                    id=faq_id
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"FAQ already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
            )
        else:
            self._log_handler.create_log(
                OperationType.CREATE,
                record_id=faq_id,
                operation_code=PortalFaq.__tablename__,
                new_data={**model.model_dump(mode="json", exclude_none=True), "id": str(faq_id)},
            )
            return UUIDBaseModel(id=faq_id)

    @distributed_trace()
    async def update_faq(self, faq_id: uuid.UUID, model: AdminFaqUpdate):
        """

        :param faq_id:
        :param model:
        :return:
        """
        try:
            await (
                self._session.insert(PortalFaq)
                .values(
                    model.model_dump(exclude_none=True),
                    id=faq_id
                )
                .on_conflict_do_update(
                    index_elements=[PortalFaq.id],
                    set_=model.model_dump(),
                )
                .execute()
            )

        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"FAQ already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
            )
        else:
            self._log_handler.create_log(
                OperationType.UPDATE,
                record_id=faq_id,
                operation_code=PortalFaq.__tablename__,
                new_data=model.model_dump(mode="json"),
            )

    @distributed_trace()
    async def delete_faq(self, faq_id: uuid.UUID, model: DeleteBaseModel) -> None:
        """

        :param faq_id:
        :param model:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(PortalFaq)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(PortalFaq.id == faq_id)
                    .execute()
                )
            else:
                await (
                    self._session.delete(PortalFaq)
                    .where(PortalFaq.id == faq_id)
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            if model.permanent:
                self._log_handler.create_log(
                    OperationType.DELETE,
                    record_id=faq_id,
                    operation_code=PortalFaq.__tablename__,
                    new_data={"deleted": True, "permanent": True},
                )
            else:
                self._log_handler.create_log(
                    OperationType.RECYCLE,
                    record_id=faq_id,
                    operation_code=PortalFaq.__tablename__,
                    new_data={"is_deleted": True, "delete_reason": model.reason},
                )

    @distributed_trace()
    async def restore_faqs(self, model: BulkAction) -> None:
        """

        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalFaq)
                .where(PortalFaq.id.in_(model.ids))
                .values(is_deleted=False)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            self._log_handler.create_log(
                OperationType.RESTORE,
                operation_code=PortalFaq.__tablename__,
                old_data={"faq_ids": [str(item) for item in model.ids]},
                new_data={"is_deleted": False},
            )

    @distributed_trace()
    async def get_category_list(self, model: DeleteQueryBaseModel) -> AdminFaqCategoryList:
        """

        :param model:
        :return:
        """
        items: Optional[list[AdminFaqCategoryBase]] = await (
            self._session.select(
                PortalFaqCategory.id,
                PortalFaqCategory.name,
                PortalFaqCategory.remark,
                PortalFaqCategory.sequence,
                PortalFaqCategory.created_at,
                PortalFaqCategory.updated_at,
            )
            .where(PortalFaqCategory.is_deleted == model.deleted)
            .order_by(PortalFaqCategory.sequence)
            .fetch(as_model=AdminFaqCategoryItem)
        )
        if not items:
            return AdminFaqCategoryList(categories=[])
        return AdminFaqCategoryList(categories=items)

    @distributed_trace()
    async def get_category_by_id(self, category_id: uuid.UUID) -> AdminFaqCategoryDetail:
        """

        :param category_id:
        :return:
        """
        item: Optional[AdminFaqCategoryDetail] = await (
            self._session.select(
                PortalFaqCategory.id,
                PortalFaqCategory.name,
                PortalFaqCategory.remark,
                PortalFaqCategory.description,
                PortalFaqCategory.created_at,
                PortalFaqCategory.updated_at,
            )
            .where(PortalFaqCategory.id == category_id)
            .where(PortalFaqCategory.is_deleted == False)
            .fetchrow(as_model=AdminFaqCategoryDetail)
        )
        if not item:
            raise NotFoundException(detail=f"FAQ Category {category_id} not found")

        return item

    @distributed_trace()
    async def create_category(self, model: AdminFaqCategoryCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        category_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalFaqCategory)
                .values(
                    model.model_dump(exclude_none=True),
                    id=category_id
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"FAQ Category {model.name} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
            )
        else:
            self._log_handler.create_log(
                OperationType.CREATE,
                record_id=category_id,
                operation_code=PortalFaqCategory.__tablename__,
                new_data={**model.model_dump(mode="json", exclude_none=True), "id": str(category_id)},
            )
            return UUIDBaseModel(id=category_id)

    @distributed_trace()
    async def update_category(self, category_id: uuid.UUID, model: AdminFaqCategoryUpdate):
        """

        :param category_id:
        :param model:
        :return:
        """
        try:
            await (
                self._session.insert(PortalFaqCategory)
                .values(
                    model.model_dump(exclude_none=True),
                    id=category_id
                )
                .on_conflict_do_update(
                    index_elements=[PortalFaqCategory.id],
                    set_=model.model_dump(),
                )
                .execute()
            )

        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"FAQ Category {model.name} already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
            )
        else:
            self._log_handler.create_log(
                OperationType.UPDATE,
                record_id=category_id,
                operation_code=PortalFaqCategory.__tablename__,
                new_data=model.model_dump(mode="json"),
            )

    @distributed_trace()
    async def delete_category(self, category_id: uuid.UUID, model: DeleteBaseModel) -> None:
        """

        :param category_id:
        :param model:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(PortalFaqCategory)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(PortalFaqCategory.id == category_id)
                    .execute()
                )
            else:
                await (
                    self._session.delete(PortalFaqCategory)
                    .where(PortalFaqCategory.id == category_id)
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            if model.permanent:
                self._log_handler.create_log(
                    OperationType.DELETE,
                    record_id=category_id,
                    operation_code=PortalFaqCategory.__tablename__,
                    new_data={"deleted": True, "permanent": True},
                )
            else:
                self._log_handler.create_log(
                    OperationType.RECYCLE,
                    record_id=category_id,
                    operation_code=PortalFaqCategory.__tablename__,
                    new_data={"is_deleted": True, "delete_reason": model.reason},
                )

    @distributed_trace()
    async def restore_categories(self, model: BulkAction) -> None:
        """

        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalFaqCategory)
                .where(PortalFaqCategory.id.in_(model.ids))
                .values(is_deleted=False)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            self._log_handler.create_log(
                OperationType.RESTORE,
                operation_code=PortalFaqCategory.__tablename__,
                old_data={"category_ids": [str(item) for item in model.ids]},
                new_data={"is_deleted": False},
            )

    @distributed_trace()
    async def change_category_sequence(self, model: AdminFaqCategoryChangeSequence) -> None:
        """

        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalFaqCategory)
                .values(sequence=model.another_sequence)
                .where(PortalFaqCategory.id == model.id)
                .execute()
            )
            await (
                self._session.update(PortalFaqCategory)
                .values(sequence=model.sequence)
                .where(PortalFaqCategory.id == model.another_id)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            self._log_handler.create_log(
                OperationType.UPDATE,
                operation_code=PortalFaqCategory.__tablename__,
                new_data=model.model_dump(mode="json"),
            )

    @distributed_trace()
    async def change_faq_sequence(self, model: AdminFaqChangeSequence) -> None:
        """

        :param model:
        :return:
        """
        category_id_a = await (
            self._session.select(PortalFaq.category_id)
            .where(PortalFaq.id == model.id)
            .where(PortalFaq.is_deleted == False)
            .fetchval()
        )
        category_id_b = await (
            self._session.select(PortalFaq.category_id)
            .where(PortalFaq.id == model.another_id)
            .where(PortalFaq.is_deleted == False)
            .fetchval()
        )
        if category_id_a is None or category_id_b is None:
            raise NotFoundException(detail="FAQ not found")
        if category_id_a != category_id_b:
            raise BadRequestException(detail="Cannot reorder FAQs across different categories")

        try:
            await (
                self._session.update(PortalFaq)
                .values(sequence=model.another_sequence)
                .where(PortalFaq.id == model.id)
                .execute()
            )
            await (
                self._session.update(PortalFaq)
                .values(sequence=model.sequence)
                .where(PortalFaq.id == model.another_id)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            self._log_handler.create_log(
                OperationType.UPDATE,
                operation_code=PortalFaq.__tablename__,
                new_data=model.model_dump(mode="json"),
            )
