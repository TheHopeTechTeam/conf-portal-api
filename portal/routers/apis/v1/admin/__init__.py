"""
Admin API routes
"""
from fastapi import APIRouter

from portal.config import settings
from .auth import router as auth_router
from .conference import router as conference_router
from .event_info import router as event_info_router
from .faq import router as faq_router
from .feedback import router as feedback_router
from .file import router as file_router
from .instructor import router as instructor_router
from .location import router as location_router
from .permission import router as permission_router
from .resource import router as resource_router
from .role import router as role_router
from .testimony import router as testimony_router
from .user import router as user_router
from .verb import router as verb_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Admin - Authentication"])
router.include_router(conference_router, prefix="/conference", tags=["Admin - Conference"])
router.include_router(event_info_router, prefix="/event_info", tags=["Admin - Event Info"])
router.include_router(faq_router, prefix="/faq", tags=["Admin - FAQ"])
router.include_router(feedback_router, prefix="/feedback", tags=["Admin - Feedback"])
router.include_router(file_router, prefix="/file", tags=["Admin - File"])
router.include_router(instructor_router, prefix="/instructor", tags=["Admin - Instructor"])
router.include_router(location_router, prefix="/location", tags=["Admin - Location"])
router.include_router(permission_router, prefix="/permission", tags=["Admin - Permission"])
router.include_router(resource_router, prefix="/resource", tags=["Admin - Resource"])
router.include_router(role_router, prefix="/role", tags=["Admin - Role"])
router.include_router(testimony_router, prefix="/testimony", tags=["Admin - Testimony"])
router.include_router(user_router, prefix="/user", tags=["Admin - User"])
router.include_router(verb_router, prefix="/verb", tags=["Admin - Verb"])

if settings.is_dev:
    from .demo import router as demo_router

    router.include_router(demo_router, prefix="/demo", tags=["Demo"])
