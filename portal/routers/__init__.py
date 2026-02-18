"""
Top level router for routers
"""
from .api_root import router as api_router
from .apis.v1.admin import router as admin_router

__all__ = [
    "api_router",
    "admin_router",
]
