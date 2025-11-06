"""
Tests for TokenBlacklistProvider.
"""
import datetime

import pytest

from portal.providers.token_blacklist_provider import TokenBlacklistProvider


@pytest.mark.asyncio
async def test_add_and_check_blacklist_token(token_blacklist_provider: TokenBlacklistProvider):
    token = "access.token.example"
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
    added = await token_blacklist_provider.add_to_blacklist(token, expires_at)
    assert added is True
    assert await token_blacklist_provider.is_blacklisted(token) is True
