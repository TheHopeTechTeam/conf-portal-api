"""
Top-level package for models.
"""
from portal.config import settings
from .conference import PortalConference, PortalConferenceInstructors
from .event_info import PortalEventSchedule
from .faq import PortalFaqCategory, PortalFaq
from .fcm_device import PortalFcmDevice, PortalFcmUserDevice
from .feedback import PortalFeedback
from .file import PortalFile, PortalFileRendition, PortalFileAssociation
from .instructor import PortalInstructor
from .language import PortalLanguage, PortalTranslation
from .location import PortalLocation
from .log import PortalLog
from .notification import PortalNotification, PortalNotificationHistory
from .rbac import (
    PortalUser,
    PortalUserProfile,
    PortalThirdPartyProvider,
    PortalUserThirdPartyAuth,
    PortalRole,
    PortalResource,
    PortalVerb,
    PortalPermission,
    PortalUserRole,
    PortalRolePermission
)
from .testimony import PortalTestimony
from .workshop import PortalWorkshop, PortalWorkshopInstructor, PortalWorkshopRegistration
from .auth import PortalAuthDevice, PortalRefreshToken

__all__ = [
    # conference
    "PortalConference",
    "PortalConferenceInstructors",
    # event_info
    "PortalEventSchedule",
    # faq
    "PortalFaqCategory",
    "PortalFaq",
    # fcm_device
    "PortalFcmDevice",
    "PortalFcmUserDevice",
    # feedback
    "PortalFeedback",
    # file
    "PortalFile",
    "PortalFileRendition",
    "PortalFileAssociation",
    # instructor
    "PortalInstructor",
    # language
    "PortalLanguage",
    "PortalTranslation",
    # location
    "PortalLocation",
    # log
    "PortalLog",
    # notification
    "PortalNotification",
    "PortalNotificationHistory",
    # rbac
    "PortalUser",
    "PortalUserProfile",
    "PortalThirdPartyProvider",
    "PortalUserThirdPartyAuth",
    "PortalRole",
    "PortalResource",
    "PortalVerb",
    "PortalPermission",
    "PortalUserRole",
    "PortalRolePermission",
    # testimony
    "PortalTestimony",
    # workshop
    "PortalWorkshop",
    "PortalWorkshopInstructor",
    "PortalWorkshopRegistration",
    # auth
    "PortalAuthDevice",
    "PortalRefreshToken",
]

if settings.is_dev:
    from .demo import Demo

    __all__.append("Demo")
