"""
FAQ handler
"""
import uuid
from typing import Optional

from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import NotFoundException
from portal.libs.consts.cache_keys import (
    CacheExpiry,
    create_faq_categories_key,
    create_faq_category_faqs_key,
    create_faq_category_key,
    create_faq_item_key,
)
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.models import PortalFaqCategory, PortalFaq
from portal.serializers.v1.faq import FaqCategoryBase, FaqCategoryList, FaqList, FaqBase


class FAQHandler:
    """FAQ handler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @distributed_trace()
    async def get_faq_categories(self) -> FaqCategoryList:
        """
        Get FAQ categories
        """
        cache_key = create_faq_categories_key()
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                return FaqCategoryList.model_validate_json(cached)
        except Exception as exc:
            logger.warning(f"get_faq_categories: failed to read cache: {exc}")
        faq_categories: Optional[list[FaqCategoryBase]] = await (
            self._session.select(
                PortalFaqCategory.id,
                PortalFaqCategory.name,
                PortalFaqCategory.description
            )
            .order_by(PortalFaqCategory.sequence)
            .fetch(as_model=FaqCategoryBase)
        )
        result = FaqCategoryList(categories=faq_categories or [])
        try:
            await self._redis.set(cache_key, result.model_dump_json(), ex=CacheExpiry.MINUTE * 30)
        except Exception as exc:
            logger.warning(f"get_faq_categories: failed to write cache: {exc}")
        return result

    @distributed_trace()
    async def get_category_by_id(self, category_id: uuid.UUID) -> Optional[FaqCategoryBase]:
        """
        Get category by ID
        """
        cache_key = create_faq_category_key(str(category_id))
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                return FaqCategoryBase.model_validate_json(cached)
        except Exception as exc:
            logger.warning(f"get_category_by_id: failed to read cache: {exc}")
        category: Optional[FaqCategoryBase] = await (
            self._session.select(
                PortalFaqCategory.id,
                PortalFaqCategory.name,
                PortalFaqCategory.description
            )
            .where(PortalFaqCategory.id == category_id)
            .fetchrow(as_model=FaqCategoryBase)
        )
        if not category:
            raise NotFoundException(detail=f"FAQ Category {category_id} not found")
        try:
            await self._redis.set(cache_key, category.model_dump_json(), ex=CacheExpiry.MINUTE * 30)
        except Exception as exc:
            logger.warning(f"get_category_by_id: failed to write cache: {exc}")
        return category

    @distributed_trace()
    async def get_faq_by_id(self, faq_id: uuid.UUID) -> Optional[FaqBase]:
        """
        Get FAQ by ID
        """
        cache_key = create_faq_item_key(str(faq_id))
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                return FaqBase.model_validate_json(cached)
        except Exception as exc:
            logger.warning(f"get_faq_by_id: failed to read cache: {exc}")
        faq: Optional[FaqBase] = await (
            self._session.select(
                PortalFaq.id,
                PortalFaq.category_id,
                PortalFaq.question,
                PortalFaq.answer,
                PortalFaq.related_link
            )
            .where(PortalFaq.id == faq_id)
            .fetchrow(as_model=FaqBase)
        )
        if not faq:
            raise NotFoundException(detail=f"FAQ {faq_id} not found")
        try:
            await self._redis.set(cache_key, faq.model_dump_json(), ex=CacheExpiry.MINUTE * 30)
        except Exception as exc:
            logger.warning(f"get_faq_by_id: failed to write cache: {exc}")
        return faq

    @distributed_trace()
    async def get_faqs_by_category(self, category_id: uuid.UUID) -> FaqList:
        """
        Get FAQs by category
        """
        cache_key = create_faq_category_faqs_key(str(category_id))
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                return FaqList.model_validate_json(cached)
        except Exception as exc:
            logger.warning(f"get_faqs_by_category: failed to read cache: {exc}")
        faqs: Optional[list[FaqBase]] = await (
            self._session.select(
                PortalFaq.id,
                PortalFaq.category_id,
                PortalFaq.question,
                PortalFaq.answer,
                PortalFaq.related_link
            )
            .where(PortalFaq.category_id == category_id)
            .order_by(PortalFaq.sequence)
            .fetch(as_model=FaqBase)
        )
        result = FaqList(faqs=faqs or [])
        try:
            await self._redis.set(cache_key, result.model_dump_json(), ex=CacheExpiry.MINUTE * 30)
        except Exception as exc:
            logger.warning(f"get_faqs_by_category: failed to write cache: {exc}")
        return result
