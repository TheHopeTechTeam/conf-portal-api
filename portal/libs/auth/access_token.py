"""
Bearer token authentication
"""
from typing import Optional

from fastapi import Request
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from portal.container import Container
from portal.exceptions.responses import UnauthorizedException, InvalidTokenException
from portal.handlers import AdminUserHandler
from portal.providers.jwt_provider import JWTProvider
from portal.providers.firebase import FirebaseProvider
from portal.libs.contexts.user_context import UserContext, set_user_context
from portal.schemas.auth import FirebaseTokenPayload
from portal.schemas.base import AccessTokenPayload
from portal.schemas.user import UserDetail


class AccessTokenAuth(HTTPBearer):
    """AccessTokenAuth"""

    def __init__(self, is_admin: bool) -> None:
        self.is_admin = is_admin
        super().__init__(auto_error=False)

    async def __call__(self, request: Request):
        result: Optional[HTTPAuthorizationCredentials] = await super().__call__(
            request=request
        )
        if not result:
            raise UnauthorizedException()
        await self.authenticate(request=request, token=result.credentials)

    async def authenticate(self, request: Request, token: str):
        """

        :param request:
        :param token:
        :return:
        """
        if self.is_admin:
            await self.verify_admin(request=request, token=token)
        await self.verify_user(request=request, token=token)

    @staticmethod
    async def verify_admin(request: Request, token: str):
        """

        :param request:
        :param token:
        :return:
        """
        container: Container = request.app.container
        jwt_provider: JWTProvider = container.jwt_provider()
        admin_user_handler: AdminUserHandler = container.admin_user_handler()
        payload: AccessTokenPayload = jwt_provider.verify_token(
            token=token,
            is_admin=True
        )
        if not payload:
            raise InvalidTokenException()

        user: UserDetail = await admin_user_handler.get_user_detail_by_id(payload.sub)
        if not user:
            raise UnauthorizedException()
        if not user.is_active or not user.is_admin or not user.verified:
            raise UnauthorizedException()
        user_context = UserContext(
            user_id=user.id,
            phone_number=user.phone_number,
            email=user.email,
            verified=user.verified,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_admin=user.is_admin,
            last_login_at=user.last_login_at,
            display_name=user.display_name,
            gender=user.gender,
            is_ministry=user.is_ministry,
            token=token,
            token_payload=payload,
            username=user.email.split("@")[0]
        )
        set_user_context(user_context)

    @staticmethod
    async def verify_user(request: Request, token: str):
        """
        TODO: refactor this method
        :param request:
        :param token:
        :return:
        """
        try:
            payload: FirebaseTokenPayload = FirebaseProvider().authentication.verify_id_token(id_token=token)
        except Exception:
            raise InvalidTokenException()



        user_context = UserContext(
            token=token,
            token_payload=payload,
            user_id=payload.user_id,
            email=payload.email,
            display_name=payload.name,
            verified=True,
        )
        set_user_context(user_context)
