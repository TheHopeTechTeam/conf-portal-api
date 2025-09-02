"""
AdminLogHandler
"""
from uuid import UUID

from portal.libs.consts.enums import OperationType
from portal.libs.database import Session
from portal.models.log import PortalLog


class AdminLogHandler:
    """AdminLogHandler"""

    def __init__(
        self,
        session: Session,
    ):
        self._session = session

    async def create_log(
        self,
        operation_type: OperationType,
        record_id: UUID = None,
        operation_code: str = None,
        old_data: dict = None,
        new_data: dict = None,
        changed_fields: list = None
    ) -> None:
        """
        Create an operation log
        :param operation_type:
        :param record_id:
        :param operation_code:
        :param old_data:
        :param new_data:
        :param changed_fields:
        :return:
        """

