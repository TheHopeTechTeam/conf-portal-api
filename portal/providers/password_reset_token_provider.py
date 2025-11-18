# portal/providers/password_reset_token_provider.py
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from portal.config import settings
from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.models import PortalPasswordResetToken


class PasswordResetTokenProvider:
    """Password Reset Token Provider"""

    def __init__(
        self,
        session: Session
    ):
        self._session = session
        self._salt = settings.PASSWORD_RESET_TOKEN_SALT
        self._token_expire_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        self._token_length = 64

    def _generate_token(self) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(self._token_length)

    def _hash_token(self, token: str) -> str:
        """Hash token for storage"""
        return hashlib.sha512(f"{self._salt}{token}".encode()).hexdigest()

    @distributed_trace()
    async def create_token(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Create password reset token
        :param user_id: User ID
        :param ip_address: IP address
        :param user_agent: User agent
        :return: Reset token
        """
        # Invalidate all existing tokens for this user
        await self._invalidate_user_tokens(user_id)

        # Generate new token
        token = self._generate_token()
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self._token_expire_minutes)

        # Store token in database
        await (
            self._session.insert(PortalPasswordResetToken)
            .values(
                user_id=user_id,
                token=token,
                token_hash=token_hash,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            .execute()
        )

        return token

    @distributed_trace()
    async def verify_token(self, token: str) -> Optional[UUID]:
        """
        Verify reset token and return user_id if valid
        :param token: Reset token
        :return: User ID if valid, None otherwise
        """
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)

        # Find valid token
        token_record: Optional[UUID] = await (
            self._session.select(
                PortalPasswordResetToken.user_id
            )
            .where(PortalPasswordResetToken.token_hash == token_hash)
            .where(PortalPasswordResetToken.expires_at > now)
            .where(PortalPasswordResetToken.used_at.is_(None))
            .fetchval()
        )

        if not token_record:
            return None

        return token_record

    @distributed_trace()
    async def mark_token_as_used(self, token: str) -> bool:
        """
        Mark token as used
        :param token: Reset token
        :return: Success status
        """
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)

        try:
            await (
                self._session.update(PortalPasswordResetToken)
                .values(used_at=now)
                .where(PortalPasswordResetToken.token_hash == token_hash)
                .where(PortalPasswordResetToken.used_at.is_(None))
                .execute()
            )
            return True
        except Exception as e:
            logger.exception(e)
            return False

    async def _invalidate_user_tokens(self, user_id: UUID) -> None:
        """Invalidate all existing tokens for a user"""
        now = datetime.now(timezone.utc)
        await (
            self._session.update(PortalPasswordResetToken)
            .values(used_at=now)
            .where(PortalPasswordResetToken.user_id == user_id)
            .where(PortalPasswordResetToken.used_at.is_(None))
            .where(PortalPasswordResetToken.expires_at > now)
            .execute()
        )
