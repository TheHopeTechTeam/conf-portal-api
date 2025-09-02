"""
Top level handlers package
"""
from portal.config import settings
from .admin import (
    AdminAuthHandler,
    AdminPermissionHandler,
    AdminResourceHandler,
    AdminRoleHandler,
)

__all__ = [
    # admin
    "AdminAuthHandler",
    "AdminPermissionHandler",
    "AdminResourceHandler",
    "AdminRoleHandler",
]

if settings.IS_DEV:
    from .demo import DemoHandler

    __all__.append("DemoHandler")
