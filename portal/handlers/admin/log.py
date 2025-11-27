"""
AdminLogHandler
"""
from uuid import UUID

from portal.libs.consts.enums import OperationType
from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace


class AdminLogHandler:
    """AdminLogHandler"""

    def __init__(
        self,
        session: Session,
    ):
        self._session = session

    @distributed_trace()
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
