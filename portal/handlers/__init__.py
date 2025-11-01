"""
Top level handlers package
"""
from portal.config import settings
from .admin.auth import AdminAuthHandler
from .admin.permission import AdminPermissionHandler
from .admin.resource import AdminResourceHandler
from .admin.role import AdminRoleHandler
from .admin.user import AdminUserHandler
from .admin.verb import AdminVerbHandler
from .conference import ConferenceHandler
from .event_info import EventInfoHandler
from .faq import FAQHandler
from .fcm_device import FCMDeviceHandler
from .feedback import FeedbackHandler
from .file import FileHandler
from .testimony import TestimonyHandler
from .user import UserHandler
from .workshop import WorkshopHandler

__all__ = [
    # admin
    "AdminAuthHandler",
    "AdminPermissionHandler",
    "AdminResourceHandler",
    "AdminRoleHandler",
    "AdminUserHandler",
    "AdminVerbHandler",
    # general
    "ConferenceHandler",
    "EventInfoHandler",
    "FAQHandler",
    "FCMDeviceHandler",
    "FeedbackHandler",
    "FileHandler",
    "TestimonyHandler",
    "UserHandler",
    "WorkshopHandler"
]

if settings.IS_DEV:
    from .admin.demo import DemoHandler

    __all__.append("DemoHandler")
