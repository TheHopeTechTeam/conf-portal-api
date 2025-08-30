"""
Bearer token authentication
"""
from typing import Optional

from fastapi import Request
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from portal.exceptions.auth import UnauthorizedException, InvalidTokenException
from portal.handlers.auth import AuthHandler
from portal.libs.contexts.api_context import APIContext, set_api_context
from portal.schemas.auth import FirebaseTokenPayload


class AccessTokenAuth(HTTPBearer):
    """AccessTokenAuth"""

    def __init__(self) -> None:
        super().__init__(auto_error=False)

    async def __call__(self, request: Request) -> Optional[APIContext]:
        result: Optional[HTTPAuthorizationCredentials] = await super().__call__(
            request=request
        )
        if not result:
            raise UnauthorizedException()
        api_context = await self.authenticate(request=request, token=result.credentials)
        set_api_context(api_context)
        return api_context

    @staticmethod
    async def authenticate(request: Request, token) -> Optional[APIContext]:
        """

        :param request:
        :param token:
        :return:
        """
        auth_handler = AuthHandler()
        try:
            payload: FirebaseTokenPayload = await auth_handler.verify_firebase_token(token=token)
        except Exception:
            raise InvalidTokenException()

        return APIContext(
            token=token,
            token_payload=payload,
            uid=payload.user_id,
            email=payload.email,
            username=payload.name,
            display_name=payload.name,
            host=request.client.host,
            url=str(request.url),
            path=request.url.path,
            verified=True,
        )
