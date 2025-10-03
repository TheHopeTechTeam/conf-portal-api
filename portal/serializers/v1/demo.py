"""
Demo serializers
"""
from typing import Optional, ClassVar

from pydantic import BaseModel, Field

from portal.libs.consts.enums import Gender
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins.base import PaginationBaseResponseModel


class DemoDetail(UUIDBaseModel):
    """
    Demo detail
    """
    name: str = Field(..., description="Name")
    remark: Optional[str] = Field(None, description="Remark")
    age: Optional[int] = Field(None, description="Age")
    gender: Optional[Gender] = Field(None, description="Gender")


class DemoList(BaseModel):
    """
    Demo list
    """
    items: Optional[list[DemoDetail]] = Field(..., description="Demo Items")


class DemoPages(PaginationBaseResponseModel):
    """
    Demo pages
    """
    items: Optional[list[DemoDetail]] = Field(..., description="Demo Items")


class DemoCreate(BaseModel):
    """
    Demo create
    """
    name: str = Field(..., description="Name")
    remark: Optional[str] = Field(None, description="Remark")
    age: Optional[int] = Field(None, description="Age")
    gender: Optional[Gender] = Field(None, description="Gender")


class DemoUpdate(DemoCreate):
    """
    Demo update
    """
