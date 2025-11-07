"""
Top level handlers package
"""
from portal.config import settings
from .admin.auth import AdminAuthHandler
from .admin.conference import AdminConferenceHandler
from .admin.faq import AdminFaqHandler
from .admin.feedback import AdminFeedbackHandler
from .admin.file import AdminFileHandler
from .admin.instructor import AdminInstructorHandler
from .admin.location import AdminLocationHandler
from .admin.permission import AdminPermissionHandler
from .admin.resource import AdminResourceHandler
from .admin.role import AdminRoleHandler
from .admin.testimony import AdminTestimonyHandler
from .admin.user import AdminUserHandler
from .admin.verb import AdminVerbHandler
from .conference import ConferenceHandler
from .event_info import EventInfoHandler
from .faq import FAQHandler
from .fcm_device import FCMDeviceHandler
from .feedback import FeedbackHandler
from .testimony import TestimonyHandler
from .user import UserHandler
from .workshop import WorkshopHandler

__all__ = [
    # admin
    "AdminAuthHandler",
    "AdminConferenceHandler",
    "AdminFaqHandler",
    "AdminFeedbackHandler",
    "AdminFileHandler",
    "AdminInstructorHandler",
    "AdminLocationHandler",
    "AdminPermissionHandler",
    "AdminResourceHandler",
    "AdminRoleHandler",
    "AdminTestimonyHandler",
    "AdminUserHandler",
    "AdminVerbHandler",
    # general
    "ConferenceHandler",
    "EventInfoHandler",
    "FAQHandler",
    "FCMDeviceHandler",
    "FeedbackHandler",
    "TestimonyHandler",
    "UserHandler",
    "WorkshopHandler"
]

if settings.is_dev:
    from .admin.demo import DemoHandler

    __all__.append("DemoHandler")
