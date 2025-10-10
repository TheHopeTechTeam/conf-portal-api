"""
Top-level package for responses of exceptions.
"""
from .base import *
from .auth import *


__all__ = [
    # base
    "ApiBaseException",
    "BadRequestException",  # 400
    "ParamError",  # 400
    "NotFoundException",  # 404
    "ResourceExistsException",  # 409
    "EntityTooLargeException",  # 413
    "NotImplementedException",  # 501
    # auth
    "InvalidTokenException",  # 401
    "UnauthorizedException",  # 401
    "RefreshTokenInvalidException",  # 401
]

