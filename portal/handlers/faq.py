"""
FAQ handler
"""
import uuid
from typing import Optional

from redis.asyncio import Redis

from portal.config import settings
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
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
        faq_categories: Optional[list[FaqCategoryBase]] = await (
            self._session.select(
                PortalFaqCategory.id,
                PortalFaqCategory.name,
                PortalFaqCategory.description
            )
            .order_by(PortalFaqCategory.sequence)
            .fetch(as_model=FaqCategoryBase)
        )
        if not faq_categories:
            return FaqCategoryList(categories=[])
        return FaqCategoryList(categories=faq_categories)

    @distributed_trace()
    async def get_category_by_id(self, category_id: uuid.UUID) -> Optional[FaqCategoryBase]:
        """
        Get category by ID
        """
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
            return None
        return category

    @distributed_trace()
    async def get_faq_by_id(self, faq_id: uuid.UUID) -> Optional[FaqBase]:
        """
        Get FAQ by ID
        """
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
            return None
        return faq

    @distributed_trace()
    async def get_faqs_by_category(self, category_id: uuid.UUID) -> FaqList:
        """
        Get FAQs by category
        """
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
        if not faqs:
            return FaqList(faqs=[])
        return FaqList(faqs=faqs)
