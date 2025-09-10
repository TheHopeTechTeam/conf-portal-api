"""
Auth Exception
"""
from typing import Optional, Dict, Any

from starlette import status

from .base import ApiBaseException


class InvalidTokenException(ApiBaseException):
    """
    Invalid Token Exception
    """

    def __init__(
        self,
        detail: str = "Invalid authorization token",
        headers: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers,
            **kwargs
        )


class UnauthorizedException(ApiBaseException):
    """
    Unauthorized Exception
    """

    def __init__(
        self,
        detail: Any = "Unauthorized",
        headers: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers,
            **kwargs
        )


class RefreshTokenInvalidException(UnauthorizedException):
    """
    Refresh Token Invalid Exception
    """
    def __init__(
        self,
        detail: Any = "Refresh token invalid",
        headers: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            detail=detail,
            headers=headers,
            **kwargs
        )
