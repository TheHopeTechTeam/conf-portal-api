"""
Feedback models
"""
import sqlalchemy as sa
from sqlalchemy import Column

from portal.libs.consts.enums import FeedbackStatus
from portal.libs.database.orm import ModelBase
from .mixins import BaseMixin


class PortalFeedback(ModelBase, BaseMixin):
    """Feedback Model"""
    name = Column(sa.String(255), nullable=False, comment="Feedback name")
    email = Column(sa.String(255), comment="Feedback email")
    message = Column(sa.Text, nullable=False, comment="Feedback message")
    status = Column(
        sa.Integer,
        default=FeedbackStatus.PENDING.value,
        comment="Feedback status"
    )
