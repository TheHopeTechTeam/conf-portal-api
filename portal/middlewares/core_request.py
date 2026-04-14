import uuid
from urllib.parse import urlparse, urlunparse

import sentry_sdk
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from portal.container import Container
from portal.libs.contexts.request_context import (
    RequestContext,
    set_request_context,
    reset_request_context,
)
from portal.libs.contexts.request_session_context import (
    set_request_session,
    reset_request_session,
)
from portal.libs.database.asyncpg_transient_errors import is_transient_asyncpg_connection_error
from portal.libs.database.transient_db_http_response import (
    safe_rollback_session,
    transient_db_503_json_response,
)
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger


def _to_scope_value(value) -> str:
    """
    Convert ASGI scope value to string.
    :param value:
    :return:
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _build_sentry_event_processor(scope_path: str, scope_root_path: str, request_id: str):
    """
    Build a Sentry event processor to normalize request URL and add ASGI scope info and request_id to event extra.
    :param scope_path:
    :param scope_root_path:
    :param request_id:
    :return:
    """
    def _processor(event, hint):
        """
        Sentry event processor to normalize request URL and add ASGI scope info and request_id to event extra.
        :param event:
        :param hint:
        :return:
        """
        request_data = (event or {}).get("request") or {}
        request_url = request_data.get("url")
        if not request_url:
            return event

        parsed_url = urlparse(request_url)
        event_path = parsed_url.path or ""
        expected_path = scope_path
        duplicated_path = f"{scope_root_path}{scope_path}" if scope_root_path else ""

        # In mounted apps, Sentry can produce root_path + path where path already contains mount prefix.
        if expected_path and duplicated_path and event_path == duplicated_path:
            request_data["url"] = urlunparse(parsed_url._replace(path=expected_path))
            event["request"] = request_data

        event.setdefault("extra", {})
        event["extra"]["asgi_scope_path"] = scope_path
        event["extra"]["asgi_scope_root_path"] = scope_root_path
        event["extra"]["request_id"] = request_id
        return event

    return _processor


def _resolve_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else None


class CoreRequestMiddleware(BaseHTTPMiddleware):

    @distributed_trace()
    async def dispatch(self, request: Request, call_next):
        req_ctx_token = None
        container: Container = request.app.container
        db_session = container.db_session()
        session_ctx_token = set_request_session(db_session)
        request_id = str(uuid.uuid4())
        scope = request.scope
        scope_path = _to_scope_value(scope.get("path"))
        scope_root_path = _to_scope_value(scope.get("root_path"))
        # Register a per-request processor so Sentry event URLs can be normalized from current ASGI scope values.
        sentry_scope = sentry_sdk.get_current_scope()
        sentry_scope.add_event_processor(
            _build_sentry_event_processor(
                scope_path=scope_path,
                scope_root_path=scope_root_path,
                request_id=request_id,
            )
        )
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
                    request_id=request_id,
                )
            )
            response = await call_next(request)
        except Exception as e:
            logger.warning(f"CoreRequestMiddleware: {e}, request_id: {request_id}")
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
