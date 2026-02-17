"""
Admin ticket type API (list for notification group selection)
"""
import time

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, status

from portal.config import settings
from portal.container import Container
from portal.libs.consts.permission import Permission
from portal.libs.consts.ticket_type_sync import (
    REDIS_KEY_TICKET_TYPE_SYNC_AT,
    TICKET_TYPE_SYNC_TTL_SECONDS,
)
from portal.libs.database import RedisPool
from portal.libs.database.session_proxy import SessionProxy
from portal.libs.events.publisher import get_event_bus
from portal.libs.events.types import TicketTypeSyncEvent
from portal.models import PortalTicketType
from portal.routers.auth_router import AuthRouter
from portal.serializers.v1.admin.ticket_type import TicketTypeListItem, TicketTypeListResponse

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/list",
    status_code=status.HTTP_200_OK,
    response_model=TicketTypeListResponse,
    description="List ticket types for notification group selection; syncs from ticket system if cache is stale",
    operation_id="admin_ticket_type_list",
    permissions=[Permission.COMMS_NOTIFICATION.read],
)
@inject
async def get_ticket_type_list(
    session: SessionProxy = Depends(Provide[Container.request_session]),
    redis_client: RedisPool = Depends(Provide[Container.redis_client]),
) -> TicketTypeListResponse:
    """
    Return ticket types (id, name). If last sync is older than TTL or never run, await sync then return.
    """
    redis = redis_client.create(db=settings.REDIS_DB)
    try:
        last_sync_raw = await redis.get(REDIS_KEY_TICKET_TYPE_SYNC_AT)
    except Exception:
        last_sync_raw = None
    last_sync = float(last_sync_raw) if last_sync_raw else 0.0
    is_stale = (time.time() - last_sync) > TICKET_TYPE_SYNC_TTL_SECONDS
    if is_stale:
        event_bus = get_event_bus()
        if event_bus:
            await event_bus.publish(TicketTypeSyncEvent())

    rows = await (
        session.select(PortalTicketType.id, PortalTicketType.name)
        .order_by(PortalTicketType.name)
        .fetch(as_model=TicketTypeListItem)
    )
    return TicketTypeListResponse(items=rows or [])
