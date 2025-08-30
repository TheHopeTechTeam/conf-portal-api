"""
Token Blacklist Provider for managing revoked tokens
"""
import hashlib
from datetime import datetime, timezone

from redis.asyncio import Redis

from portal.config import settings
from portal.libs.consts.cache_keys import (
    get_token_blacklist_key,
    get_refresh_token_blacklist_key,
    get_token_blacklist_pattern,
    get_refresh_token_blacklist_pattern,
)
from portal.libs.database import RedisPool


class TokenBlacklistProvider:
    """Token Blacklist Provider for managing revoked tokens"""

    def __init__(self, redis_client: RedisPool):
        self.redis: Redis = redis_client.create(db=settings.REDIS_DB)

    def _get_token_hash(self, token: str) -> str:
        """Generate hash for token to use as Redis key"""
        return hashlib.sha256(token.encode()).hexdigest()

    def _get_blacklist_key(self, token: str) -> str:
        """Get Redis key for blacklist token"""
        token_hash = self._get_token_hash(token)
        return get_token_blacklist_key(token_hash)

    def _get_refresh_blacklist_key(self, token: str) -> str:
        """Get Redis key for blacklisted refresh token"""
        token_hash = self._get_token_hash(token)
        return get_refresh_token_blacklist_key(token_hash)

    async def add_to_blacklist(self, token: str, expires_at: datetime) -> bool:
        """
        Add token to blacklist with expiration
        """
        try:
            key = self._get_blacklist_key(token)
            # Calculate TTL in seconds
            ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())

            if ttl > 0:
                await self.redis.setex(key, ttl, "1")
                return True
            return False
        except Exception:
            return False

    async def add_refresh_token_to_blacklist(self, token: str, expires_at: datetime) -> bool:
        """
        Add refresh token to blacklist with expiration
        """
        try:
            key = self._get_refresh_blacklist_key(token)
            # Calculate TTL in seconds
            ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())

            if ttl > 0:
                await self.redis.setex(key, ttl, "1")
                return True
            return False
        except Exception:
            return False

    async def is_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted
        """
        try:
            key = self._get_blacklist_key(token)
            exists = await self.redis.exists(key)
            return bool(exists)
        except Exception:
            return False

    async def is_refresh_token_blacklisted(self, token: str) -> bool:
        """
        Check if refresh token is blacklisted
        """
        try:
            key = self._get_refresh_blacklist_key(token)
            exists = await self.redis.exists(key)
            return bool(exists)
        except Exception:
            return False

    async def remove_from_blacklist(self, token: str) -> bool:
        """
        Remove token from blacklist (for testing purposes)
        """
        try:
            key = self._get_blacklist_key(token)
            result = await self.redis.delete(key)
            return bool(result)
        except Exception:
            return False

    async def get_blacklist_stats(self) -> dict:
        """
        Get blacklist statistics (for monitoring)
        """
        try:
            blacklist_keys = await self.redis.keys(get_token_blacklist_pattern())
            refresh_blacklist_keys = await self.redis.keys(get_refresh_token_blacklist_pattern())

            return {
                "blacklisted_tokens": len(blacklist_keys),
                "blacklisted_refresh_tokens": len(refresh_blacklist_keys),
                "total_blacklisted": len(blacklist_keys) + len(refresh_blacklist_keys)
            }
        except Exception:
            return {
                "blacklisted_tokens": 0,
                "blacklisted_refresh_tokens": 0,
                "total_blacklisted": 0
            }
