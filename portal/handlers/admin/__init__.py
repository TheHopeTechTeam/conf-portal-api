"""
Admin handlers
"""
from .auth import AdminAuthHandler
from .permission import AdminPermissionHandler
from .resource import AdminResourceHandler
from .role import AdminRoleHandler

__all__ = [
    "AdminAuthHandler",
    "AdminPermissionHandler",
    "AdminResourceHandler",
    "AdminRoleHandler",
]

