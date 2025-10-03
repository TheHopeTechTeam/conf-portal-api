"""
User Serializers
"""
from typing import Optional

from pydantic import Field

from portal.schemas.mixins import UUIDBaseModel
from portal.schemas.user import SUserDetail
from portal.serializers.mixins import PaginationBaseResponseModel



class UserTableItem(SUserDetail):
    """UserTableItem"""
    pass


class UserPages(PaginationBaseResponseModel):
    """UserPages"""
    items: Optional[list[UserTableItem]] = Field(..., description="Items")
