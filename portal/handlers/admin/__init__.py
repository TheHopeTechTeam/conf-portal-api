"""
Admin handlers
"""
from .auth import AdminAuthHandler
from .resource import AdminResourceHandler
from .permission import AdminPermissionHandler

__all__ = [
    "AdminAuthHandler",
    "AdminResourceHandler",
    "AdminPermissionHandler",
]
