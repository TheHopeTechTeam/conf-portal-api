"""
AdminTestimonyHandler
"""
from typing import Optional

import sqlalchemy as sa
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import NotFoundException
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalTestimony
from portal.serializers.v1.admin.testimony import (
    AdminTestimonyQuery,
    AdminTestimonyItem,
    AdminTestimonyDetail,
    AdminTestimonyPages,
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

    @distributed_trace()
    async def get_testimony_pages(self, model: AdminTestimonyQuery) -> AdminTestimonyPages:
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
                as_model=AdminTestimonyItem
            )
        )
        return AdminTestimonyPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def get_testimony_by_id(self, testimony_id: str) -> AdminTestimonyDetail:
        """

        :param testimony_id:
        :return:
        """
        item: Optional[AdminTestimonyDetail] = await (
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
            .fetchrow(as_model=AdminTestimonyDetail)
        )
        if not item:
            raise NotFoundException(detail=f"Testimony {testimony_id} not found")
        return item
