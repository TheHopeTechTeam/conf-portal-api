"""
FeedbackHandler
"""
import uuid

from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import PortalFeedback
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.v1.feedback import FeedbackCreate


class FeedbackHandler:
    """FeedbackHandler"""

    def __init__(
        self,
        session: Session,
    ):
        self._session = session

    @distributed_trace()
    async def creat_feedback(self, model: FeedbackCreate) -> UUIDBaseModel:
        """
        Create feedback
        """
        feedback_id = uuid.uuid4()
        await (
            self._session.insert(PortalFeedback)
            .values(
                model.model_dump(exclude_none=True),
                id=feedback_id,
            )
            .execute()
        )
        return UUIDBaseModel(id=feedback_id)
