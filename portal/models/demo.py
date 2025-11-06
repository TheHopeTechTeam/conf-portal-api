"""
Model of the demo table
"""
from sqlalchemy import Column, Integer, String

from portal.libs.consts.enums import Gender
from portal.libs.database.orm import ModelBase
from .mixins import AuditMixin, DeletedMixin, RemarkMixin


class Demo(ModelBase, RemarkMixin, DeletedMixin, AuditMixin):
    """Demo Model for demonstration purposes"""
    __tablename__ = "demo"
    name = Column(String(16), nullable=False, unique=True, comment="Name, unique identifier")
    age = Column(Integer, comment="Age")
    password = Column(String(32), comment="Password")
    gender = Column(Integer, default=Gender.UNKNOWN.value, comment="Refer to Gender enum")
