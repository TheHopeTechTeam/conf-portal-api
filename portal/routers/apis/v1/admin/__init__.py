"""
Admin API routes
"""
from fastapi import APIRouter

from .auth import router as auth_router
from .permission import router as permission_router
from .resource import router as resource_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Admin - Authentication"])
router.include_router(permission_router, prefix="/permission", tags=["Admin - Permission"])
router.include_router(resource_router, prefix="/resource", tags=["Admin - Resource"])
