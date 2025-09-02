"""
Admin handler fixtures for testing.
"""
from .auth import admin_auth_handler
from .permission import admin_permission_handler

__all__ = [
    "admin_auth_handler",
    "admin_permission_handler",
]
