"""
AdminFaqHandler
"""
import uuid
from typing import Optional

from asyncpg import UniqueViolationError
from redis.asyncio import Redis

import sqlalchemy as sa
from portal.config import settings
from portal.exceptions.responses import NotFoundException, ConflictErrorException, ApiBaseException
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalFaq, PortalFaqCategory
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction, DeleteQueryBaseModel
from portal.serializers.v1.admin.faq import (
    AdminFaqQuery,
    AdminFaqBase,
    AdminFaqPages,
    AdminFaqDetail,
    AdminFaqCreate,
    AdminFaqUpdate,
    AdminFaqCategoryBase,
    AdminFaqCategoryItem,
    AdminFaqCategoryList,
    AdminFaqCategoryDetail,
    AdminFaqCategoryCreate,
    AdminFaqCategoryUpdate, AdminFaqItem,
)


class AdminFaqHandler:
    """AdminFaqHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    async def get_faq_pages(self, model: AdminFaqQuery) -> AdminFaqPages:
        """

        :param model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalFaq.id,
                PortalFaqCategory.name.label("category_name"),
                PortalFaq.question,
                PortalFaq.related_link,
                PortalFaq.remark,
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
            .order_by_with(
                tables=[PortalFaq],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=AdminFaqItem
            )
        )
        return AdminFaqPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

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

