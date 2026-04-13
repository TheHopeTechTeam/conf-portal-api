import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from portal.container import Container
from portal.libs.database.asyncpg_transient_errors import is_transient_asyncpg_connection_error
from portal.libs.database.transient_db_http_response import (
    safe_rollback_session,
    transient_db_503_json_response,
)
from portal.libs.contexts.request_context import (
    RequestContext,
    set_request_context,
    reset_request_context,
)
from portal.libs.contexts.request_session_context import (
    set_request_session,
    reset_request_session,
)


def _resolve_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else None


class CoreRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_ctx_token = None
        container: Container = request.app.container
        db_session = container.db_session()
        session_ctx_token = set_request_session(db_session)
        try:
            # initialize request context
            req_ctx_token = set_request_context(
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
        except Exception as e:
            await safe_rollback_session(db_session)
            if is_transient_asyncpg_connection_error(e):
                return transient_db_503_json_response(request, e)
            raise e
        else:
            if response.status_code < 400:
                await db_session.commit()
            else:
                await db_session.rollback()
            return response
        finally:
            if req_ctx_token is not None:
                reset_request_context(req_ctx_token)
            await db_session.close()
            reset_request_session(session_ctx_token)
            # container.reset_singletons()
