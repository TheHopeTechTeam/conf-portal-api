"""
Testimony models
"""
import sqlalchemy as sa
from sqlalchemy import Column

from portal.libs.database.orm import ModelBase
from .mixins import BaseMixin


class PortalTestimony(ModelBase, BaseMixin):
    """Testimony Model"""
    name = Column(sa.String(255), nullable=False, comment="Testimony name")
    phone_number = Column(sa.String(16), comment="Phone number")
    share = Column(sa.Boolean, default=False, comment="Share permission")
    message = Column(sa.Text, nullable=False, comment="Testimony message")
