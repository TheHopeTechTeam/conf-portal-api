"""
Check-in token provider: creates and verifies one-time JWT for ticket check-in QR codes.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
from redis.asyncio import Redis

from portal.config import settings
from portal.libs.consts.cache_keys import get_check_in_token_used_key
from portal.libs.database import RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger


class CheckInTokenProvider:
    """Creates and verifies one-time check-in tokens for QR codes."""

    def __init__(self, redis_client: RedisPool):
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)
        self._secret_key = settings.JWT_SECRET_KEY
        self._algorithm = "HS256"
        self._audience = f"{settings.APP_NAME}-check-in"
        self._expire_seconds = settings.CHECK_IN_TOKEN_EXPIRE_SECONDS

    @distributed_trace()
    def create_token(self, ticket_id: uuid.UUID) -> tuple[str, datetime]:
        """
        Create a signed one-time check-in token.
        :param ticket_id: Ticket ID
        :return: (token string, expires_at datetime)
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._expire_seconds)
        jti = str(uuid.uuid4())
        payload = {
            "ticket_id": str(ticket_id),
            "exp": int(expires_at.timestamp()),
            "iat": int(now.timestamp()),
            "iss": settings.BASE_URL,
            "aud": self._audience,
            "jti": jti,
        }
        token = jwt.encode(
            payload,
            self._secret_key,
            algorithm=self._algorithm,
        )
        return token, expires_at

    @distributed_trace()
    async def verify_and_consume_token(self, token: str) -> tuple[Optional[uuid.UUID], bool]:
        """
        Verify token and consume it (mark jti as used).
        :param token: JWT string
        :return: (ticket_id, already_used). ticket_id is None when invalid/expired.
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=settings.BASE_URL,
            )
        except jwt.PyJWTError as e:
            logger.warning(f"Check-in token verification failed: {e}")
            return None, False

        jti = payload.get("jti")
        ticket_id_str = payload.get("ticket_id")
        if not jti or not ticket_id_str:
            return None, False

        try:
            ticket_id = uuid.UUID(ticket_id_str)
        except (ValueError, TypeError):
            return None, False

        used_key = get_check_in_token_used_key(jti)
        if await self._redis.exists(used_key):
            logger.warning(f"Check-in token already used: jti={jti}")
            return ticket_id, True

        exp = payload.get("exp")
        ttl = max(exp - int(datetime.now(timezone.utc).timestamp()), 60)
        await self._redis.setex(used_key, ttl, "1")

        return ticket_id, False
