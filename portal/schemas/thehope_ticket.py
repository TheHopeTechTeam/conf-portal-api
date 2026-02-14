"""
The Hope Ticket API response schemas.

Implements BaseModels for GET /api/v1/tickets response (TicketsListResponse)
and nested Tickets structure from the external OpenAPI spec.
"""
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class TheHopeBaseResponse(BaseModel):
    """Base response schema for all endpoints."""

    model_config = ConfigDict(populate_by_name=True)

    total_docs: Optional[int] = Field(None, alias="totalDocs")
    limit: Optional[int] = Field(None)
    total_pages: Optional[int] = Field(None, alias="totalPages")
    page: Optional[int] = Field(None)
    paging_counter: Optional[int] = Field(None, alias="pagingCounter")
    has_prev_page: Optional[bool] = Field(None, alias="hasPrevPage")
    has_next_page: Optional[bool] = Field(None, alias="hasNextPage")
    prev_page: Optional[int | None] = Field(None, alias="prevPage")
    next_page: Optional[int | None] = Field(None, alias="nextPage")

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, "docs"):
            raise ValueError("items field is required")


class TheHopeTicketUser(BaseModel):
    """User (CMS backend user) reference in ticket response."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID = Field(..., description="資料唯一識別碼")
    name: Optional[str] = Field(None, description="CMS 後台使用者 user 的全名")
    email: Optional[str] = Field(None, description="CMS 後台使用者 user 的 email 地址")
    role: Optional[str] = Field(None, description="CMS 後台使用者 user 的身份")


class TheHopeTicketMember(BaseModel):
    """Member reference in ticket response (owner / user)."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID = Field(..., description="資料唯一識別碼")
    email: Optional[str] = Field(None, description="Email")
    name: Optional[str] = Field(None, description="名稱 - 請填寫全名")
    gender: Optional[str] = Field(None, description="male / female / unknown")
    tel: Optional[str] = Field(None, description="聯絡電話")
    role: Optional[str] = Field(None, description="會眾身份")
    location: Optional[str] = Field(None, description="所屬教會")


class TheHopeTicketType(BaseModel):
    """Ticket type reference in ticket response."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID = Field(..., description="資料唯一識別碼")
    name: Optional[str] = Field(None, description="票種名稱")
    is_member_info_required: Optional[bool] = Field(None, alias="isMemberInfoRequired")
    price: Optional[float] = Field(None, description="單張票價")
    bundle_size: Optional[int] = Field(None, alias="bundleSize", description="套票人數")
    max_tickets: Optional[int] = Field(None, alias="maxTickets", description="可售票數上限")
    sold: Optional[int] = Field(None, description="已售數量")
    image: Optional[str] = Field(None, description="圖片")
    caption: Optional[str] = Field(None, description="注意事項")
    description: Optional[Any] = Field(None, description="內容")
    meta: Optional[dict[str, Any]] = Field(None, description="自定義欄位")


class TheHopeTicketOrderItem(BaseModel):
    """Order item reference (minimal for order items in response)."""

    model_config = ConfigDict(populate_by_name=True)

    id: Optional[UUID] = Field(None, description="資料唯一識別碼")
    quantity: Optional[int] = Field(None, description="數量")
    price_at_purchase: Optional[float] = Field(None, alias="priceAtPurchase")


class TheHopeTicketOrder(BaseModel):
    """Order reference in ticket response."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID = Field(..., description="資料唯一識別碼")
    status: Optional[str] = Field(None, description="pending / completed / failed / refunded")
    total: Optional[float] = Field(None, description="訂單總額")
    tap_pay_trade_id: Optional[str] = Field(None, alias="tapPayTradeId")
    member: Optional[TheHopeTicketMember | str] = Field(None, description="關聯到 members 的資料")
    items: Optional[list[TheHopeTicketOrderItem | dict[str, Any]]] = Field(None, description="訂單項目")
    tickets: Optional[list[dict[str, Any]]] = Field(None, description="票券")


class TheHopeTicket(BaseModel):
    """
    Single ticket item from GET /api/v1/tickets (Tickets schema).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: UUID = Field(..., description="資料唯一識別碼")
    order: TheHopeTicketOrder | str = Field(..., description="關聯到 orders 的資料")
    ticket_type: TheHopeTicketType | str = Field(..., alias="type", description="關聯到 ticketTypes 的資料")
    owner: Optional[TheHopeTicketMember | str] = Field(None, description="關聯到 members 的資料")
    user: Optional[TheHopeTicketMember | str] = Field(None, description="關聯到 members 的資料")
    is_redeemed: Optional[bool] = Field(None, alias="isRedeemed", description="是否已取票")
    is_checked_in: Optional[bool] = Field(None, alias="isCheckedIn", description="是否已報到")


class TheHopeTicketTypesResponse(TheHopeBaseResponse):
    """
    Response schema for GET /api/v1/ticketTypes (TicketTypes schema).
    """
    docs: list[TheHopeTicketType] = Field(default_factory=list, description="TicketType documents")


class TheHopeTicketsListResponse(TheHopeBaseResponse):
    """
    Response schema for GET /api/v1/tickets (TicketsListResponse).
    """
    docs: list[TheHopeTicket] = Field(default_factory=list, description="Ticket documents")
