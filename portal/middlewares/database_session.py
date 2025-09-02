"""
Middleware for custom http
"""
from fastapi import Request, Response
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from portal.container import Container


class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    """Database Session Middleware"""

    async def dispatch(self, request: Request, call_next):
        container: Container = request.app.container
        db_session = container.db_session()
        try:
            response: Response = await call_next(request)
        except Exception:
            print("Error in database session middleware")
            await db_session.rollback()
            raise
        else:
            await db_session.commit()
            return response
        finally:
            container.reset_singletons()
