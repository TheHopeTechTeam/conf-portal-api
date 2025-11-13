"""
JWT Provider for DI
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

import jwt

from portal.config import settings
from portal.libs.consts.enums import AccessTokenAudType
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.providers.token_blacklist_provider import TokenBlacklistProvider
from portal.schemas.base import AccessTokenPayload


class JWTProvider:
    """JWT Token Provider"""

    def __init__(self, token_blacklist_provider: TokenBlacklistProvider):
        self.token_blacklist_provider = token_blacklist_provider
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self._issuer = settings.BASE_URL
        self._audience = settings.APP_NAME

    @distributed_trace()
    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        display_name: str,
        family_id: UUID,
        roles: list = None,
        permissions: list = None,
        aud_type: AccessTokenAudType = AccessTokenAudType.APP,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """

        :param aud_type:
        :param user_id:
        :param email:
        :param display_name:
        :param family_id:
        :param roles:
        :param permissions:
        :param expires_delta:
        :return:
        """
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self.access_token_expire_minutes)

        access_token_payload = None
        match aud_type:
            case AccessTokenAudType.ADMIN:
                access_token_payload = AccessTokenPayload(
                    iss=self._issuer,
                    exp=int(expire.timestamp()),
                    sub=user_id,
                    aud=self._audience + "-admin",
                    iat=int(now.timestamp()),
                    user_id=user_id,
                    email=email,
                    display_name=display_name,
                    roles=roles,
                    permissions=permissions,
                    family_id=family_id
                )
            case AccessTokenAudType.APP:
                access_token_payload = AccessTokenPayload(
                    iss=self._issuer,
                    exp=int(expire.timestamp()),
                    sub=user_id,
                    aud=self._audience + "-app",
                    iat=int(now.timestamp()),
                    user_id=user_id,
                    email=email,
                    display_name=display_name,
                    family_id=family_id
                )
            case _:
                raise ValueError(f"Invalid access token aud type: {aud_type}")
        if not access_token_payload:
            raise ValueError("Invalid access token payload")
        encoded_jwt = jwt.encode(
            access_token_payload.model_dump(mode="json", exclude_none=True),
            self.secret_key,
            algorithm=self.algorithm,
        )
        return encoded_jwt

    def verify_token(self, token: str, is_admin: bool = True, **kwargs) -> Optional[AccessTokenPayload]:
        """
        Verify and decode token
        :param token:
        :param is_admin:
        :param kwargs:
        :return:
        """
        try:
            audience = self._audience + "-app" if not is_admin else self._audience + "-admin"
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=audience,
                issuer=self._issuer,
                **kwargs
            )
            return AccessTokenPayload.model_validate(payload)
        except jwt.PyJWTError as e:
            logger.error(f"Error decoding JWT: {e}")
            return None

    def is_token_expired(self, token: str, is_admin: bool = True) -> bool:
        """
        Check if token is expired
        """
        payload: AccessTokenPayload = self.verify_token(
            token=token,
            is_admin=is_admin
        )
        if not payload:
            return True

        if not payload.exp:
            return True

        return datetime.now(timezone.utc) > datetime.fromtimestamp(payload.exp, tz=timezone.utc)

    def is_admin_token(self, token: str) -> bool:
        """
        Check if token is for admin user
        """
        payload: AccessTokenPayload = self.verify_token(
            token=token,
            is_admin=True
        )
        if not payload:
            return False

        return payload.iss == self._issuer

    def is_user_token(self, token: str) -> bool:
        """
        Check if token is for frontend user
        """

    async def verify_token_with_blacklist(self, token: str, is_admin: bool = True) -> Optional[AccessTokenPayload]:
        """
        Verify token and check if it's blacklisted
        """
        # First verify the token
        payload: AccessTokenPayload = self.verify_token(
            token=token,
            is_admin=is_admin,
            options={"verify_signature": False}
        )
        if not payload:
            return None

        # Check if token is blacklisted
        if await self.token_blacklist_provider.is_blacklisted(token):
            return None

        return payload

    # Deprecated: refresh tokens are opaque and managed by RefreshTokenProvider
    def get_token_expiration(self, token: str, is_admin: bool = True) -> Optional[datetime]:
        """
        Get token expiration time
        """
        payload: AccessTokenPayload = self.verify_token(
            token=token,
            is_admin=is_admin,
            options={"verify_signature": False}
        )
        if not payload:
            return None
        if not payload.exp:
            return None
        return datetime.fromtimestamp(payload.exp, tz=timezone.utc)
