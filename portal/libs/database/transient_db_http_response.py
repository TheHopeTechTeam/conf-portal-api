"""
Shared HTTP payload and rollback helpers for transient asyncpg / connection errors.
"""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette import status

from portal.config import settings


async def safe_rollback_session(session) -> None:
    if session is None:
        return
    try:
        await session.rollback()
    except Exception:
        pass


def transient_db_503_content(request: Request, exc: BaseException) -> dict[str, Any]:
    content: dict[str, Any] = {
        "detail": {
            "message": "Service Unavailable",
            "url": str(request.url),
        },
        "code": "db_transient",
    }
    if settings.is_dev:
        content["debug_detail"] = f"{exc.__class__.__name__}: {exc}"
    return content


def transient_db_503_json_response(request: Request, exc: BaseException) -> JSONResponse:
    return JSONResponse(
        content=transient_db_503_content(request, exc),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
