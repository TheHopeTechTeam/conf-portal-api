"""
Handler for demo-related operations
"""
import uuid
from uuid import UUID

import sqlalchemy as sa
from asyncpg import UniqueViolationError

from portal.exceptions.responses import ResourceExistsException, ApiBaseException
from portal.libs.database import Session
from portal.models import Demo
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, DeleteBaseModel
from portal.serializers.v1.demo import DemoDetail, DemoList, DemoPages, DemoUpdate, DemoCreate


class DemoHandler:
    """DemoHandler"""

    def __init__(
        self,
        session: Session = None,
    ):
        """initialize"""
        self._session = session

    async def get_pages(
        self,
        model: GenericQueryBaseModel
    ) -> DemoPages:
        """
        Get demo pages
        :param model:
        :return:
        """
        items, total = await (
            self._session.select(
                Demo.id,
                Demo.name,
                Demo.remark,
                Demo.age,
                Demo.gender,
            )
            .where(Demo.is_deleted == model.deleted)
            .where(
                model.keyword, lambda: sa.or_(
                    Demo.name.ilike(f"%{model.keyword}%"),
                    Demo.remark.ilike(f"%{model.keyword}%")
                )
            )
            .order_by_with(
                tables=[Demo],
                order_by=model.order_by,
                descending=model.descending
            )
            .limit(model.page_size)
            .offset(model.page * model.page_size)
            .fetchpages(as_model=DemoDetail)
        )
        return DemoPages(
            items=items,
            total=total,
            page=model.page,
            page_size=model.page_size
        )

    async def create_demo(self, model: DemoCreate) -> UUIDBaseModel:
        """

        :param model:
        :return:
        """
        demo_id = uuid.uuid4()
        try:
            await self._session.insert(Demo).values(
                name=model.name,
                remark=model.remark,
                age=model.age,
                gender=model.gender,
            ).execute()
        except UniqueViolationError as e:
            raise ResourceExistsException(
                detail="Demo with the same name already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )
        else:
            return UUIDBaseModel(id=demo_id)

    async def update_demo(self, demo_id: uuid.UUID, model: DemoUpdate) -> None:
        """

        :param demo_id:
        :param model:
        :return:
        """
        try:
            result = await (
                self._session.insert(Demo)
                .values(
                    model.model_dump(exclude_none=True),
                    id=demo_id,
                )
                .on_conflict_do_update(
                    index_elements=[Demo.id],
                    set_=model.model_dump(),
                )
                .execute()
            )
            if result == 0:
                raise ApiBaseException(
                    status_code=404,
                    detail="Demo not found",
                )
        except UniqueViolationError as e:
            raise ResourceExistsException(
                detail="Demo with the same name already exists",
                debug_detail=str(e),
            )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    async def delete_demo(self, demo_id: UUID, model: DeleteBaseModel) -> None:
        """

        :param demo_id:
        :param model:
        :return:
        """
        try:
            if not model.permanent:
                await (
                    self._session.update(Demo)
                    .values(is_deleted=True, delete_reason=model.reason)
                    .where(Demo.id == demo_id)
                    .execute()
                )
            else:
                await (
                    self._session.delete(Demo)
                    .where(Demo.id == demo_id)
                    .execute()
                )
        except Exception as e:
            raise ApiBaseException(
                status_code=500,
                detail="Internal Server Error",
                debug_detail=str(e),
            )

    async def get_list(
        self
    ) -> DemoList:
        """
        Get demo list
        :return:
        """
        items = await (
            self._session.select(
                Demo.id,
                Demo.name,
                Demo.remark
            )
            .fetch(as_model=DemoDetail)
        )
        return DemoList(items=items)
