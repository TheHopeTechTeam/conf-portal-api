"""
Root router.
"""
from collections import defaultdict

from fastapi import APIRouter, Request, status
from fastapi.openapi.utils import get_openapi

from .apis.v1 import router as api_v1_router
from ..config import settings

router = APIRouter()
router.include_router(api_v1_router, prefix="/v1")


@router.get(
    path="/healthz"
)
async def healthz():
    """
    Healthcheck endpoint
    :return:
    """
    return {
        "message": "ok"
    }

@router.get(
    path="/openapi.json",
    status_code=status.HTTP_200_OK,
)
async def custom_openapi(
    request: Request,
) -> dict:
    """

    :param request:
    :return:
    """
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        summary="Conferences Portal API",
        description="API documentation for Conferences Portal",
        routes=request.app.routes,
    )
    raw_paths = openapi_schema["paths"]
    new_paths = defaultdict()
    for path, methods in raw_paths.items():  # type: str, dict
        if path.startswith("/api/v1") and "admin" not in path:
            new_paths[path] = methods
    openapi_schema["paths"] = new_paths

    return openapi_schema
