import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from portal.libs.contexts.request_context import (
    RequestContext,
    set_request_context,
    request_context_var,
)


def _resolve_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else None


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_token = None
        try:
            # initialize request context
            request_token = set_request_context(
                RequestContext(
                    ip=_resolve_ip(request),
                    client_ip=(request.client.host if request.client else None),
                    user_agent=request.headers.get("user-agent"),
                    method=request.method,
                    host=(request.headers.get("host") or request.url.hostname),
                    url=str(request.url),
                    path=request.url.path,
                    request_id=str(uuid.uuid4()),
                )
            )
            response = await call_next(request)
            return response
        finally:
            if request_token is not None:
                request_context_var.reset(request_token)


