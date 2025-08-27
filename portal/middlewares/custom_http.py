"""
Middleware for custom http
"""
from fastapi import Request, Response
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from portal.container import Container


class CustomHTTPMiddleware(BaseHTTPMiddleware):
    """Custom HTTP Middleware"""

    async def dispatch(self, request: Request, call_next):
        try:
            response: Response = await call_next(request)
            return response
        except RuntimeError as exc:
            if str(exc) == 'No response returned.' and await request.is_disconnected():
                return Response(status_code=status.HTTP_204_NO_CONTENT)
            raise
        finally:
            container: Container = request.app.container
            container.reset_singletons()
