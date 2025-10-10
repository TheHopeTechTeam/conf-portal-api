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
from .fcm_device import FCMDeviceHandler
from .file import FileHandler
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
    "FCMDeviceHandler",
    "FileHandler",
    "UserHandler",
]

if settings.IS_DEV:
    from .admin.demo import DemoHandler

    __all__.append("DemoHandler")
