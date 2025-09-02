"""
JWT Provider for DI
"""
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from portal.config import settings
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.providers.token_blacklist_provider import TokenBlacklistProvider

from portal.schemas.base import AccessTokenPayload


class JWTProvider:
    """JWT Token Provider"""

    def __init__(self, token_blacklist_provider: TokenBlacklistProvider):
        self.token_blacklist_provider = token_blacklist_provider
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self._issuer = settings.APP_NAME.replace("-", "_")

    @distributed_trace()
    def create_admin_access_token(
        self,
        user_id: UUID,
        email: str,
        display_name: str,
        family_id: UUID,
        roles: list = None,
        permissions: list = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create access token for admin users
        """
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self.access_token_expire_minutes)

        access_token_payload = AccessTokenPayload(
            iss=self._issuer,
            exp=int(expire.timestamp()),
            sub=f"{self._issuer}_admin_access",
            aud=f"{self._issuer}_admin",
            iat=int(now.timestamp()),
            user_id=user_id,
            email=email,
            display_name=display_name,
            roles=roles or [],
            permissions=permissions or [],
            family_id=family_id
        )

        # Use Pydantic JSON mode to ensure UUIDs are serialized to strings
        encoded_jwt = jwt.encode(
            access_token_payload.model_dump(mode="json", exclude_none=True),
            self.secret_key,
            algorithm=self.algorithm,
        )
        return encoded_jwt

    def create_user_access_token(
        self,
        subject: str,
        user_id: UUID,
        email: str,
        display_name: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create access token for frontend users
        """

    def verify_token(self, token: str, is_admin: bool = True, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Verify and decode token
        TODO: adjust return type
        :param token:
        :param is_admin:
        :param kwargs:
        :return:
        """
        if is_admin:
            kwargs["audience"] = f"{self._issuer}_admin"
            kwargs["subject"] = f"{self._issuer}_admin_access"
            kwargs["issuer"] = self._issuer
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                **kwargs
            )
            return payload
        except jwt.PyJWTError:
            return None

    def is_token_expired(self, token: str, is_admin: bool = True) -> bool:
        """
        Check if token is expired
        """
        payload = self.verify_token(
            token=token,
            is_admin=is_admin
        )
        if not payload:
            return True

        exp = payload.get("exp")
        if not exp:
            return True

        return datetime.now(timezone.utc) > datetime.fromtimestamp(exp)

    def is_admin_token(self, token: str) -> bool:
        """
        Check if token is for admin user
        TODO: adjust return condition
        """
        payload = self.verify_token(
            token=token,
            is_admin=True
        )
        if not payload:
            return False

        token_type = payload.get("sub")
        return token_type in [f"{self._issuer}_admin_access"]

    def is_user_token(self, token: str) -> bool:
        """
        Check if token is for frontend user
        """

    async def verify_token_with_blacklist(self, token: str, is_admin: bool = True) -> Optional[Dict[str, Any]]:
        """
        Verify token and check if it's blacklisted
        """
        # First verify the token
        payload = self.verify_token(
            token=token,
            is_admin=is_admin,
            options={"verify_signature": False}
        )
        if not payload:
            return None

        # Check if token is blacklisted
        if self.token_blacklist_provider and await self.token_blacklist_provider.is_blacklisted(token):
            return None

        return payload

    # Deprecated: refresh tokens are opaque and managed by RefreshTokenProvider

    def get_token_expiration(self, token: str, is_admin: bool = True) -> Optional[datetime]:
        """
        Get token expiration time
        """
        payload = self.verify_token(
            token=token,
            is_admin=is_admin,
            options={"verify_signature": False}
        )
        if not payload:
            return None

        exp = payload.get("exp")
        if not exp:
            return None

        return datetime.fromtimestamp(exp, tz=timezone.utc)
