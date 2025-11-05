"""
AdminTestimonyHandler
"""
from typing import Optional

import sqlalchemy as sa
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import NotFoundException, ApiBaseException
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalTestimony
from portal.serializers.v1.admin.testimony import (
    TestimonyQuery,
    TestimonyItem,
    TestimonyDetail,
    TestimonyPages,
)


class AdminTestimonyHandler:
    """AdminTestimonyHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    async def get_testimony_pages(self, model: TestimonyQuery) -> TestimonyPages:
        """

        :param model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalTestimony.id,
                PortalTestimony.name,
                PortalTestimony.phone_number,
                PortalTestimony.share,
                PortalTestimony.remark,
                PortalTestimony.created_at,
                PortalTestimony.updated_at,
            )
            .where(PortalTestimony.is_deleted == model.deleted)
            .where(model.share is not None, lambda: PortalTestimony.share == model.share)
            .where(
                model.keyword is not None, lambda: sa.or_(
                    PortalTestimony.name.ilike(f"%{model.keyword}%"),
                    PortalTestimony.phone_number.ilike(f"%{model.keyword}%")
                )
            )
            .order_by_with(
                tables=[PortalTestimony],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=TestimonyItem
            )
        )
        return TestimonyPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def get_testimony_by_id(self, testimony_id: str) -> TestimonyDetail:
        """

        :param testimony_id:
        :return:
        """
        item: Optional[TestimonyDetail] = await (
            self._session.select(
                PortalTestimony.id,
                PortalTestimony.name,
                PortalTestimony.phone_number,
                PortalTestimony.share,
                PortalTestimony.message,
                PortalTestimony.remark,
                PortalTestimony.description,
                PortalTestimony.created_at,
                PortalTestimony.updated_at,
            )
            .where(PortalTestimony.id == testimony_id)
            .fetchrow(as_model=TestimonyDetail)
        )
        if not item:
            raise NotFoundException(detail=f"Testimony {testimony_id} not found")
        return item
