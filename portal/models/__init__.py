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

__all__ = [
    # rbac
    "PortalUser",
    "PortalUserProfile",
    "PortalThirdPartyProvider",
    "PortalUserThirdPartyAuth",
    "PortalRole",
    "PortalResource",
    "PortalVerb",
    "PortalPermission"
]

if settings.IS_DEV:
    from .demo import Demo

    __all__.append("Demo")
