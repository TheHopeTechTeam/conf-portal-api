"""
Root router.
"""
from fastapi import APIRouter

from portal.libs.depends import DEFAULT_RATE_LIMITERS
from .apis.v1 import router as api_v1_router

router = APIRouter(
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ],
)
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
