"""
Top level handlers package
"""
from portal.config import settings
from .admin.auth import AdminAuthHandler
from .admin.permission import AdminPermissionHandler
from .admin.resource import AdminResourceHandler
from .admin.role import AdminRoleHandler
from .admin.user import AdminUserHandler
from .conference import ConferenceHandler
from .event_info import EventInfoHandler
from .faq import FAQHandler
from .fcm_device import FCMDeviceHandler
from .feedback import FeedbackHandler
from .file import FileHandler
from .testimony import TestimonyHandler
from .user import UserHandler

__all__ = [
    # admin
    "AdminAuthHandler",
    "AdminPermissionHandler",
    "AdminResourceHandler",
    "AdminRoleHandler",
    "AdminUserHandler",
    # general
    "ConferenceHandler",
    "EventInfoHandler",
    "FAQHandler",
    "FCMDeviceHandler",
    "FeedbackHandler",
    "FileHandler",
    "TestimonyHandler",
    "UserHandler",
]

if settings.IS_DEV:
    from .admin.demo import DemoHandler

    __all__.append("DemoHandler")
