"""
Top level handlers package
"""
from portal.config import settings
from .admin import (
    AdminAuthHandler,
    AdminResourceHandler
)

__all__ = [
    # admin
    "AdminAuthHandler",
    "AdminResourceHandler",
]


if settings.IS_DEV:
    from .demo import DemoHandler

    __all__.append("DemoHandler")
