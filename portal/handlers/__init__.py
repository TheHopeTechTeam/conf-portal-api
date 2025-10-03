"""
Top level handlers package
"""
from portal.config import settings
from .admin.auth import AdminAuthHandler
from .admin.permission import AdminPermissionHandler
from .admin.resource import AdminResourceHandler
from .admin.role import AdminRoleHandler
from .admin.user import AdminUserHandler

__all__ = [
    # admin
    "AdminAuthHandler",
    "AdminPermissionHandler",
    "AdminResourceHandler",
    "AdminRoleHandler",
    "AdminUserHandler"
]

if settings.IS_DEV:
    from .admin.demo import DemoHandler

    __all__.append("DemoHandler")
