import asyncio
from typing import Optional, Any, Callable

from portal.libs.database import Session
from portal.libs.contexts.event_session_context import get_event_session
from portal.libs.contexts.request_session_context import get_request_session


class SessionProxy:
    """
    A lightweight proxy that forwards attribute access/calls to the Session
    in ContextVar.
    1. Resolves to event-scoped session first (when running in event handler)
    2. If not available, resolves to request-scoped session (when running in API request)
    """

    def __init__(self) -> None:
        # Intentionally stateless; session is resolved per access from context
        self._noop: Optional[Callable[..., Any]] = None

    def _resolve(self) -> Session:
        session = get_event_session()
        if session is not None:
            return session
        session = get_request_session()
        if session is None:
            raise RuntimeError("No Session is available in context (neither event nor request scope)")
        return session

    def __getattr__(self, name: str) -> Any:
        session = self._resolve()
        attr = getattr(session, name)
        if asyncio.iscoroutinefunction(attr):
            async def _wrapped(*args, **kwargs):
                return await attr(*args, **kwargs)

            return _wrapped
        return attr


