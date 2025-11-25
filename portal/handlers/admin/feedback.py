"""
AdminFeedbackHandler
"""
import uuid
from typing import Optional

import sqlalchemy as sa
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import NotFoundException, ApiBaseException
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalFeedback
from portal.serializers.v1.admin.feedback import (
    AdminFeedbackQuery,
    AdminFeedbackItem,
    AdminFeedbackDetail,
    AdminFeedbackPages,
    AdminFeedbackUpdate,
)


class AdminFeedbackHandler:
    """AdminFeedbackHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    async def get_feedback_pages(self, model: AdminFeedbackQuery) -> AdminFeedbackPages:
        """

        :param model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalFeedback.id,
                PortalFeedback.name,
                PortalFeedback.email,
                PortalFeedback.message,
                PortalFeedback.status,
                PortalFeedback.remark,
                PortalFeedback.created_at,
                PortalFeedback.updated_at,
            )
            .where(PortalFeedback.is_deleted == model.deleted)
            .where(model.status is not None, lambda: PortalFeedback.status == model.status)
            .where(
                model.keyword is not None, lambda: sa.or_(
                    PortalFeedback.name.ilike(f"%{model.keyword}%"),
                    PortalFeedback.email.ilike(f"%{model.keyword}%"),
                )
            )
            .order_by_with(
                tables=[PortalFeedback],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=AdminFeedbackItem
            )
        )
        return AdminFeedbackPages(
            page=model.page,
            page_size=model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def get_feedback_by_id(self, feedback_id: str) -> AdminFeedbackDetail:
        """

        :param feedback_id:
        :return:
        """
        item: Optional[AdminFeedbackDetail] = await (
            self._session.select(
                PortalFeedback.id,
                PortalFeedback.name,
                PortalFeedback.email,
                PortalFeedback.message,
                PortalFeedback.status,
                PortalFeedback.remark,
                PortalFeedback.description,
                PortalFeedback.created_at,
                PortalFeedback.updated_at,
            )
            .where(PortalFeedback.id == feedback_id)
            .fetchrow(as_model=AdminFeedbackDetail)
        )
        if not item:
            raise NotFoundException(detail=f"Feedback {feedback_id} not found")
        return item

    @distributed_trace()
    async def update_feedback(self, feedback_id: uuid.UUID, model: AdminFeedbackUpdate) -> None:
        """

        :param feedback_id:
        :param model:
        :return:
        """
        try:
            await (
                self._session.update(PortalFeedback)
                .values(model.model_dump())
                .where(PortalFeedback.id == feedback_id)
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
