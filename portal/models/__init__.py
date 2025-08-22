"""
Top-level package for models.
"""
from portal.config import settings


__all__ = [
]

if settings.IS_DEV:
    from .demo import Demo

    __all__.append("Demo")
