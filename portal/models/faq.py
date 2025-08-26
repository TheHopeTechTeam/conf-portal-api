"""
FAQ models
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

from portal.libs.database.orm import ModelBase
from .mixins import BaseMixin, SortableMixin


class PortalFaqCategory(ModelBase, BaseMixin, SortableMixin):
    """FAQ Category Model"""
    name = Column(sa.String(255), nullable=False, comment="Category name")
    description = Column(sa.Text, comment="Category description")


class PortalFaq(ModelBase, BaseMixin, SortableMixin):
    """FAQ Model"""
    category_id = Column(
        UUID,
        sa.ForeignKey(PortalFaqCategory.id, ondelete="CASCADE"),
        nullable=False,
        comment="Category ID",
        index=True
    )
    question = Column(sa.Text, nullable=False, comment="FAQ question")
    answer = Column(sa.Text, nullable=False, comment="FAQ answer")
    related_link = Column(sa.String(500), comment="Related link URL")
