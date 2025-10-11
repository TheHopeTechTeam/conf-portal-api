"""
Top level router for v1 API
"""
from fastapi import APIRouter

from portal.config import settings
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.route_classes import LogRoute
from .account import router as account_router
from .admin import router as admin_router
from .conference import router as conference_router
from .event_info import router as event_info_router
from .faq import router as faq_router
from .fcm_device import router as fcm_device_router
from .feedback import router as feedback_router
from .testimony import router as testimony_router
from .workshop import router as workshop_router

router = APIRouter(
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ],
    route_class=LogRoute
)
router.include_router(admin_router, prefix="/admin", tags=["Admin"])

router.include_router(account_router, prefix="/account", tags=["Account"])
router.include_router(conference_router, prefix="/conference", tags=["Conference"])
router.include_router(event_info_router, prefix="/event_info", tags=["Event Info"])
router.include_router(faq_router, prefix="/faq", tags=["FAQ"])
router.include_router(fcm_device_router, prefix="/fcm_device", tags=["FCM Device"])
router.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
router.include_router(testimony_router, prefix="/testimony", tags=["Testimony"])
# router.include_router(workshop_router, prefix="/workshop", tags=["Workshop"])
