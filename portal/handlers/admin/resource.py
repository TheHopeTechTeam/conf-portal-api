"""
Handler for admin resource
"""
from portal.libs.database import Session
from portal.serializers.mixins import GenericQueryBaseModel


class AdminResourceHandler:
    """AdminResourceHandler"""

    def __init__(
        self,
        db_session: Session = None,
    ):
        self._db_session = db_session


    async def get_resources_page(
        self,
        query_model: GenericQueryBaseModel
    ):
        """

        :param query_model:
        :return:
        """

