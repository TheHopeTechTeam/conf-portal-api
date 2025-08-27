"""
Top level handlers package
"""
from .file import FileHandler
from .auth import AuthHandler
from .account import AccountHandler
from .conference import ConferenceHandler
from .event_info import EventInfoHandler
from .faq import FAQHandler
from .fcm_device import FCMDeviceHandler
from .feedback import FeedbackHandler
from .testimony import TestimonyHandler
from .workshop import WorkshopHandler

__all__ = [
    # auth
    "AuthHandler",
    # account
    "AccountHandler",
    # conference
    "ConferenceHandler",
    # event_info
    "EventInfoHandler",
    # faq
    "FAQHandler",
    # fcm_device
    "FCMDeviceHandler",
    # feedback
    "FeedbackHandler",
    # file
    "FileHandler",
    # testimony
    "TestimonyHandler",
    # workshop
    "WorkshopHandler"
]

from ..config import settings

if settings.IS_DEV:
    from .demo import DemoHandler

    __all__.append("DemoHandler")
