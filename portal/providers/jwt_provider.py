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


class JWTProvider:
    """JWT Token Provider"""

    def __init__(self, token_blacklist_provider: TokenBlacklistProvider):
        self.token_blacklist_provider = token_blacklist_provider
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    @distributed_trace()
    def create_admin_access_token(
        self,
        subject: str,
        user_id: UUID,
        email: str,
        display_name: str,
        roles: list = None,
        permissions: list = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create access token for admin users
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode = {
            "sub": subject,
            "user_id": str(user_id),
            "email": email,
            "display_name": display_name,
            "roles": roles or [],
            "permissions": permissions or [],
            "exp": expire,
            "type": "admin_access"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    @distributed_trace()
    def create_admin_refresh_token(
        self,
        subject: str,
        user_id: UUID,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create refresh token for admin users
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        to_encode = {
            "sub": subject,
            "user_id": str(user_id),
            "exp": expire,
            "type": "admin_refresh"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
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
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode = {
            "sub": subject,
            "user_id": str(user_id),
            "email": email,
            "display_name": display_name,
            "exp": expire,
            "type": "user_access"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_user_refresh_token(
        self,
        subject: str,
        user_id: UUID,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create refresh token for frontend users
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        to_encode = {
            "sub": subject,
            "user_id": str(user_id),
            "exp": expire,
            "type": "user_refresh"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode token
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None

    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired
        """
        payload = self.verify_token(token)
        if not payload:
            return True

        exp = payload.get("exp")
        if not exp:
            return True

        return datetime.now(timezone.utc) > datetime.fromtimestamp(exp)

    def is_admin_token(self, token: str) -> bool:
        """
        Check if token is for admin user
        """
        payload = self.verify_token(token)
        if not payload:
            return False

        token_type = payload.get("type")
        return token_type in ["admin_access", "admin_refresh"]

    def is_user_token(self, token: str) -> bool:
        """
        Check if token is for frontend user
        """
        payload = self.verify_token(token)
        if not payload:
            return False

        token_type = payload.get("type")
        return token_type in ["user_access", "user_refresh"]

    async def verify_token_with_blacklist(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify token and check if it's blacklisted
        """
        # First verify the token
        payload = self.verify_token(token)
        if not payload:
            return None

        # Check if token is blacklisted
        if self.token_blacklist_provider and await self.token_blacklist_provider.is_blacklisted(token):
            return None

        return payload

    async def verify_refresh_token_with_blacklist(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify refresh token and check if it's blacklisted
        """
        # First verify the token
        payload = self.verify_token(token)
        if not payload:
            return None

        # Check if refresh token is blacklisted
        if self.token_blacklist_provider and await self.token_blacklist_provider.is_refresh_token_blacklisted(token):
            return None

        return payload

    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Get token expiration time
        """
        payload = self.verify_token(token)
        if not payload:
            return None

        exp = payload.get("exp")
        if not exp:
            return None

        return datetime.fromtimestamp(exp, tz=timezone.utc)
