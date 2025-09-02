"""
Tests for TokenBlacklistProvider.
"""
import datetime

import pytest

from portal.config import settings
from portal.container import Container


@pytest.mark.asyncio
async def test_add_and_check_blacklist_token(container: Container):
    token = "access.token.example"
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
    added = await container.token_blacklist_provider().add_to_blacklist(token, expires_at)
    assert added is True
    assert await container.token_blacklist_provider().is_blacklisted(token) is True


@pytest.mark.asyncio
async def test_add_and_check_refresh_blacklist_token(container: Container):
    token = "refresh.token.example"
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
    added = await container.token_blacklist_provider().add_refresh_token_to_blacklist(token, expires_at)
    assert added is True
    assert await container.token_blacklist_provider().is_refresh_token_blacklisted(token) is True


@pytest.mark.asyncio
async def test_remove_from_blacklist(container: Container):
    token = "something-to-remove"
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
    await container.token_blacklist_provider().add_to_blacklist(token, expires_at)
    assert await container.token_blacklist_provider().is_blacklisted(token) is True
    removed = await container.token_blacklist_provider().remove_from_blacklist(token)
    assert removed is True
    assert await container.token_blacklist_provider().is_blacklisted(token) is False


@pytest.mark.asyncio
async def test_get_blacklist_stats(container: Container):
    # ensure clean
    stats = await container.token_blacklist_provider().get_blacklist_stats()
    total_before = stats["total_blacklisted"]

    # add two new unique keys so stats strictly increase
    now = datetime.datetime.now(datetime.timezone.utc)
    await container.token_blacklist_provider().add_to_blacklist(f"a:{now.timestamp()}", now + datetime.timedelta(minutes=5))
    await container.token_blacklist_provider().add_refresh_token_to_blacklist(f"b:{now.timestamp()}", now + datetime.timedelta(minutes=5))

    stats_after = await container.token_blacklist_provider().get_blacklist_stats()
    assert stats_after["total_blacklisted"] >= total_before + 2


