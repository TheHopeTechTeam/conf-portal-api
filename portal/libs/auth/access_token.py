"""
Bearer token authentication
"""
from typing import Optional

from fastapi import Request
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from portal.exceptions.auth import UnauthorizedException, InvalidTokenException
from portal.handlers.auth import AuthHandler
from portal.libs.contexts.user_context import UserContext, get_user_context
from portal.schemas.auth import FirebaseTokenPayload


class AccessTokenAuth(HTTPBearer):
    """AccessTokenAuth"""

    def __init__(self) -> None:
        super().__init__(auto_error=False)

    async def __call__(self, request: Request) -> Optional[UserContext]:
        result: Optional[HTTPAuthorizationCredentials] = await super().__call__(
            request=request
        )
        if not result:
            raise UnauthorizedException()
        user_context = await self.authenticate(request=request, token=result.credentials)
        # mutate only, do not set ContextVar here
        current = get_user_context()
        current.user_id = user_context.user_id
        current.email = user_context.email
        current.username = user_context.username
        current.display_name = user_context.display_name
        current.token = user_context.token
        current.token_payload = user_context.token_payload
        current.verified = user_context.verified
        return current

    @staticmethod
    async def authenticate(request: Request, token) -> Optional[UserContext]:
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

        return UserContext(
            token=token,
            token_payload=payload,
            user_id=payload.user_id,
            email=payload.email,
            username=payload.name,
            display_name=payload.name,
            verified=True,
        )
