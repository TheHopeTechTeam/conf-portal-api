"""
Location models
"""
import sqlalchemy as sa
from sqlalchemy import Column

from portal.libs.database.orm import ModelBase
from .mixins import BaseMixin


class PortalLocation(ModelBase, BaseMixin):
    """Location Model"""
    name = Column(sa.String(255), nullable=False, comment="Location name")
    address = Column(sa.Text, comment="Location address")
    floor = Column(sa.String(10), comment="Floor number")
    room_number = Column(sa.String(10), comment="Room number")
    latitude = Column(sa.DECIMAL(9, 6), comment="Latitude coordinate")
    longitude = Column(sa.DECIMAL(9, 6), comment="Longitude coordinate")
