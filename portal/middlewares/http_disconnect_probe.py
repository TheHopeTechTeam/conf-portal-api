"""
ASGI middleware: log when the server receives http.disconnect on the receive channel.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from portal.libs.contexts.request_context import get_request_context
from portal.libs.logger import logger


class HttpDisconnectProbeMiddleware:
    """
    Outermost-friendly ASGI middleware (not BaseHTTPMiddleware).
    Wraps receive to observe http.disconnect for observability.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def receive_wrapper() -> Message:
            message = await receive()
            if message["type"] == "http.disconnect":
                path = scope.get("path") or ""
                if isinstance(path, bytes):
                    path = path.decode("utf-8", errors="replace")
                req_ctx = get_request_context()
                request_id = (
                    req_ctx.request_id
                    if req_ctx is not None and req_ctx.request_id
                    else None
                )
                if request_id:
                    logger.info(f"HttpDisconnectProbeMiddleware: http.disconnect received. path={path}, request_id={request_id}")
                else:
                    logger.info(f"HttpDisconnectProbeMiddleware: http.disconnect received. path={path}, request_id=None")
            return message

        await self.app(scope, receive_wrapper, send)
