"""
Admin API routes
"""
from fastapi import APIRouter

from portal.config import settings
from .auth import router as auth_router
from .file import router as file_router
from .permission import router as permission_router
from .resource import router as resource_router
from .role import router as role_router
from .user import router as user_router
from .verb import router as verb_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Admin - Authentication"])
router.include_router(file_router, prefix="/file", tags=["Admin - File"])
router.include_router(permission_router, prefix="/permission", tags=["Admin - Permission"])
router.include_router(resource_router, prefix="/resource", tags=["Admin - Resource"])
router.include_router(role_router, prefix="/role", tags=["Admin - Role"])
router.include_router(user_router, prefix="/user", tags=["Admin - User"])
router.include_router(verb_router, prefix="/verb", tags=["Admin - Verb"])

if settings.IS_DEV:
    from .demo import router as demo_router

    router.include_router(demo_router, prefix="/demo", tags=["Demo"])
