"""
TestimonyHandler
"""
import uuid

from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalTestimony
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.testimony import TestimonyCreate


class TestimonyHandler:
    """TestimonyHandler"""

    def __init__(
        self,
        session: Session,
    ):
        self._session = session

    @distributed_trace()
    async def create_testimony(self, model: TestimonyCreate) -> UUIDBaseModel:
        """
        Create testimony
        """
        testimony_id = uuid.uuid4()
        await (
            self._session.insert(PortalTestimony)
            .values(
                model.model_dump(exclude_none=True),
                id=testimony_id,
            )
            .execute()
        )
        return UUIDBaseModel(id=testimony_id)
