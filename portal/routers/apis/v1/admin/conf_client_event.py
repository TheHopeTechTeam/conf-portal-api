"""
Conf-frontend client telemetry (no auth; mounted from api_root without v1-wide rate limits).
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Request, status

from portal.container import Container
from portal.handlers.conf_client_event import ConfClientEventHandler
from portal.routers.auth_router import AuthRouter

router: AuthRouter = AuthRouter(require_auth=False)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED
)
@inject
async def post_conf_client_event(
    request: Request,
    conf_client_event_handler: ConfClientEventHandler = Depends(Provide[Container.conf_client_event_handler]),
) -> dict[str, bool]:
    """
    Ingest sanitized client diagnostics. Always returns 201 with {"accepted": true}.
    """
    raw_body = await request.body()
    return await conf_client_event_handler.ingest(raw_body=raw_body)
