"""
Top level handlers package
"""
from .admin.auth import AdminAuthHandler
from .admin.conference import AdminConferenceHandler
from .admin.demo import DemoHandler
from .admin.event_info import AdminEventInfoHandler
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
from .user_auth import UserAuthHandler
from .workshop import WorkshopHandler

__all__ = [
    # demo
    "DemoHandler",
    # admin
    "AdminAuthHandler",
    "AdminConferenceHandler",
    "AdminEventInfoHandler",
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
    "UserAuthHandler",
    "WorkshopHandler"
]
