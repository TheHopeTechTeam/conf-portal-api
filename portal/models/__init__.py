"""
Top-level package for models.
"""
from portal.config import settings
from .rbac import (
    PortalUser,
    PortalUserProfile,
    PortalThirdPartyProvider,
    PortalUserThirdPartyAuth,
    PortalRole,
    PortalResource,
    PortalVerb,
    PortalPermission
)
from .file import PortalFile, PortalFileRendition, PortalFileAssociation
from .log import PortalLog

__all__ = [
    # rbac
    "PortalUser",
    "PortalUserProfile",
    "PortalThirdPartyProvider",
    "PortalUserThirdPartyAuth",
    "PortalRole",
    "PortalResource",
    "PortalVerb",
    "PortalPermission",
    # file
    "PortalFile",
    "PortalFileRendition",
    "PortalFileAssociation",
    # system log
    "PortalLog",
]

if settings.IS_DEV:
    from .demo import Demo

    __all__.append("Demo")
