"""
Instructor models
"""
import sqlalchemy as sa
from sqlalchemy import Column

from portal.libs.database.orm import ModelBase
from .mixins import BaseMixin, SortableMixin


class PortalInstructor(ModelBase, BaseMixin, SortableMixin):
    """Instructor Model"""
    name = Column(sa.String(255), nullable=False, comment="Instructor name")
    title = Column(sa.String(255), comment="Instructor title")
    bio = Column(sa.Text, comment="Instructor biography")
