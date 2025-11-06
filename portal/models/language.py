"""
Language models
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

from portal.libs.database.orm import ModelBase
from .mixins import BaseMixin


class PortalLanguage(ModelBase, BaseMixin):
    """Language Model"""
    code = Column(sa.String(10), nullable=False, unique=True, comment="Language code")
    name = Column(sa.String(50), nullable=False, comment="Language name")
    is_active = Column(sa.Boolean, default=True, comment="Is language active")


class PortalTranslation(ModelBase, BaseMixin):
    """Translation Model"""
    __extra_table_args__ = (
        sa.UniqueConstraint("content_type", "object_id", "language_id", "field_name"),
    )
    language_id = Column(
        UUID,
        sa.ForeignKey(PortalLanguage.id, ondelete="CASCADE"),
        nullable=False,
        comment="Language ID",
        index=True
    )
    content_type = Column(sa.String(50), nullable=False, comment="Content type")
    object_id = Column(UUID, nullable=False, comment="Object ID")
    field_name = Column(sa.String(50), nullable=False, comment="Field name")
    translated_text = Column(sa.Text, nullable=False, comment="Translated text")
