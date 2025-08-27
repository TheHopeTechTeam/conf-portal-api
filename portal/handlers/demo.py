"""
Handler for demo-related operations
"""
from portal.libs.database import Session
from portal.models import Demo
from portal.serializers.mixins import GenericQueryBaseModel
from portal.serializers.v1.demo import DemoDetail, DemoList, DemoPages


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
        query_model: GenericQueryBaseModel
    ) -> DemoPages:
        """
        Get demo pages
        :param query_model:
        :return:
        """
        items, total = await (
            self._session.select(
                Demo.id,
                Demo.name,
                Demo.remark
            )
            .limit(query_model.page_size)
            .offset(query_model.page * query_model.page_size)
            .fetchpages(as_model=DemoDetail)
        )
        return DemoPages(
            items=items,
            total=total,
            page=query_model.page,
            page_size=query_model.page_size
        )

    async def create_record(
        self,
        model: DemoDetail
    ):
        """

        :param model:
        :return:
        """
        try:
            await self._session.insert(Demo).values(
                name=model.name,
                remark=model.remark
            ).execute()
        except Exception as e:
            await self._session.rollback()
            raise e
        else:
            await self._session.commit()
        finally:
            await self._session.close()

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
        return DemoList(
            items=items
        )
