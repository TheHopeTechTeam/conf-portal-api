"""
AdminWorkshopRegistrationHandler
"""
import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from redis.asyncio import Redis

from portal.config import settings
from portal.exceptions.responses import NotFoundException, ConflictErrorException, ApiBaseException
from portal.libs.database import Session, RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalWorkshopRegistration, PortalWorkshop, PortalUser, PortalUserProfile
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.v1.admin.workshop_registration import (
    WorkshopRegistrationQuery,
    WorkshopRegistrationPages,
    WorkshopRegistrationItem,
    WorkshopRegistrationDetail,
    WorkshopRegistrationCreate,
)


class AdminWorkshopRegistrationHandler:
    """AdminWorkshopRegistrationHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @distributed_trace()
    async def get_workshop_registration_pages(self, query_model: WorkshopRegistrationQuery) -> WorkshopRegistrationPages:
        """
        Get workshop registration pages
        :param query_model:
        :return:
        """
        items, count = await (
            self._session.select(
                PortalWorkshopRegistration.id,
                PortalWorkshopRegistration.registered_at,
                PortalWorkshopRegistration.unregistered_at,
                PortalWorkshop.title.label("workshop_title"),
                PortalUser.email.label("user_email"),
                PortalUserProfile.display_name.label("user_display_name"),
            )
            .outerjoin(PortalWorkshop, PortalWorkshopRegistration.workshop_id == PortalWorkshop.id)
            .outerjoin(PortalUser, PortalWorkshopRegistration.user_id == PortalUser.id)
            .outerjoin(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(PortalWorkshopRegistration.is_deleted == query_model.deleted)
            .where(query_model.workshop_id is not None, lambda: PortalWorkshopRegistration.workshop_id == query_model.workshop_id)
            .where(
                query_model.is_registered is not None,
                lambda: (
                    PortalWorkshopRegistration.unregistered_at.is_(None) if query_model.is_registered
                    else PortalWorkshopRegistration.unregistered_at.isnot(None)
                )
            )
            .where(
                query_model.keyword,
                lambda: sa.or_(
                    PortalWorkshop.title.ilike(f"%{query_model.keyword}%"),
                    PortalUser.email.ilike(f"%{query_model.keyword}%"),
                    PortalUserProfile.display_name.ilike(f"%{query_model.keyword}%"),
                )
            )
            .order_by_with(
                tables=[PortalWorkshopRegistration],
                order_by=query_model.order_by,
                descending=query_model.descending
            )
            .limit(query_model.page_size)
            .offset(query_model.page * query_model.page_size)
            .fetchpages(
                no_order_by=False,
                as_model=WorkshopRegistrationItem
            )
        )

        return WorkshopRegistrationPages(
            page=query_model.page,
            page_size=query_model.page_size,
            total=count,
            items=items
        )

    @distributed_trace()
    async def get_workshop_registration_by_id(self, registration_id: uuid.UUID) -> WorkshopRegistrationDetail:
        """
        Get workshop registration by ID
        :param registration_id:
        :return:
        """
        item: Optional[WorkshopRegistrationDetail] = await (
            self._session.select(
                PortalWorkshopRegistration.id,
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalWorkshop.id, sa.String),
                    sa.cast("title", sa.VARCHAR(255)), PortalWorkshop.title,
                ).label("workshop"),
                sa.func.json_build_object(
                    sa.cast("id", sa.VARCHAR(40)), sa.cast(PortalUser.id, sa.String),
                    sa.cast("phone_number", sa.VARCHAR(16)), PortalUser.phone_number,
                    sa.cast("email", sa.VARCHAR(255)), PortalUser.email,
                    sa.cast("display_name", sa.VARCHAR(64)), PortalUserProfile.display_name
                ).label("user"),
            )
            .outerjoin(PortalWorkshop, PortalWorkshopRegistration.workshop_id == PortalWorkshop.id)
            .outerjoin(PortalUser, PortalWorkshopRegistration.user_id == PortalUser.id)
            .outerjoin(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .where(PortalWorkshopRegistration.id == registration_id)
            .where(PortalWorkshopRegistration.is_deleted == False)
            .fetchrow(as_model=WorkshopRegistrationDetail)
        )

        if not item:
            raise NotFoundException(detail=f"Workshop registration {registration_id} not found")
        return item

    @distributed_trace()
    async def create_workshop_registration(self, model: WorkshopRegistrationCreate) -> UUIDBaseModel:
        """
        Create workshop registration
        :param model:
        :return:
        """
        registration_id = uuid.uuid4()
        try:
            await (
                self._session.insert(PortalWorkshopRegistration)
                .values(
                    id=registration_id,
                    workshop_id=model.workshop_id,
                    user_id=model.user_id,
                    registered_at=datetime.now(),
                    unregistered_at=None,
                )
                .execute()
            )
        except UniqueViolationError as e:
            raise ConflictErrorException(
                detail=f"User {model.user_id} has already registered for workshop {model.workshop_id}",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=registration_id)

    @distributed_trace()
    async def unregister_workshop_registration(self, registration_id: uuid.UUID) -> None:
        """
        Unregister workshop registration
        :param registration_id:
        :return:
        """
        # Check if registration exists and is currently registered
        registration = await (
            self._session.select(
                PortalWorkshopRegistration.id,
                PortalWorkshopRegistration.registered_at,
                PortalWorkshopRegistration.unregistered_at,
            )
            .where(PortalWorkshopRegistration.id == registration_id)
            .where(PortalWorkshopRegistration.is_deleted == False)
            .fetchrow(as_model=WorkshopRegistrationItem)
        )

        if not registration:
            raise NotFoundException(detail=f"Workshop registration {registration_id} not found")

        if registration.unregistered_at is not None:
            raise ConflictErrorException(detail="Workshop registration is already unregistered")

        try:
            await (
                self._session.update(PortalWorkshopRegistration)
                .where(PortalWorkshopRegistration.id == registration_id)
                .values(unregistered_at=datetime.now())
                .execute()
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    @distributed_trace()
    async def delete_workshop_registration(self, registration_id: uuid.UUID, model: DeleteBaseModel) -> None:
        """
        Delete workshop registration
        :param registration_id:
        :param model:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(PortalWorkshopRegistration)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(PortalWorkshopRegistration.id == registration_id)
                    .execute()
                )
            else:
                await (
                    self._session.delete(PortalWorkshopRegistration)
                    .where(PortalWorkshopRegistration.id == registration_id)
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )




