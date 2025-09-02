"""
Tests for RefreshTokenProvider.
"""
import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from portal.libs.database.session_mock import SessionMock
from portal.models.auth import PortalRefreshToken, PortalAuthDevice
from portal.providers.refresh_token_provider import RefreshTokenProvider
from portal.schemas.base import RefreshTokenData


@pytest.mark.asyncio
async def test_issue_inserts_device_and_token(request_context, refresh_token_provider: RefreshTokenProvider):
    user_id = uuid4()
    device_id = uuid4()
    family_id = uuid4()

    # mock device upsert execute and token insert execute
    refresh_token_provider._session = SessionMock()
    refresh_token_provider._session.insert(PortalAuthDevice).mock()
    refresh_token_provider._session.insert(PortalRefreshToken).mock()

    rt = await refresh_token_provider.issue(user_id=user_id, device_id=device_id, family_id=family_id)
    refresh_token_provider._generate_token.assert_called_once()
    refresh_token_provider._hash_token.assert_called_once()
    assert isinstance(rt, str)

@pytest.mark.asyncio
async def test_rotate_success(request_context, refresh_token_provider: RefreshTokenProvider):
    # existing token row
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_rt = "rt-1"
    mock_rt2 = "rt-2"
    mock_rt_hash = "hash-1"
    mock_rt_hash2 = "hash-2"
    rt_row = RefreshTokenData(
        user_id=uuid4(),
        device_id=uuid4(),
        family_id=uuid4(),
        token_hash="hash-1",
        expires_at=now + datetime.timedelta(days=1),
        last_used_at=now,
        revoked_at=None,
        revoked_reason=None,
    )

    refresh_token_provider._session = SessionMock()
    refresh_token_provider._session.select(PortalRefreshToken).where(PortalRefreshToken.token_hash == mock_rt_hash).mock_fetchrow(return_value=rt_row)
    refresh_token_provider._session.update(PortalAuthDevice).mock(return_value=None)
    refresh_token_provider._session.insert(PortalRefreshToken).mock(return_value=None)
    refresh_token_provider._session.update(PortalRefreshToken).mock(return_value=None)

    refresh_token_provider._generate_token = Mock(return_value=mock_rt2)
    refresh_token_provider._hash_token = Mock(side_effect=[mock_rt_hash, mock_rt_hash2])
    rt, new_rt_data = await refresh_token_provider.rotate(mock_rt)
    assert isinstance(new_rt_data, RefreshTokenData)
    assert new_rt_data.token_hash != rt_row.token_hash
    assert new_rt_data.token_hash == mock_rt_hash2
    assert rt == mock_rt2
    assert new_rt_data.family_id == rt_row.family_id


@pytest.mark.asyncio
async def test_rotate_invalid_when_not_found(request_context, refresh_token_provider: RefreshTokenProvider):
    refresh_token_provider._session = SessionMock()
    refresh_token_provider._session.select(PortalRefreshToken).where(PortalRefreshToken.token_hash == "missing").mock_fetchrow(return_value=None)
    with pytest.raises(Exception):
        await refresh_token_provider.rotate("missing")


@pytest.mark.asyncio
async def test_revoke_family_updates_rows(request_context, refresh_token_provider: RefreshTokenProvider):
    refresh_token_provider._session = SessionMock()
    refresh_token_provider._session.update(PortalRefreshToken).mock(return_value=None)
    await refresh_token_provider.revoke_family(family_id=uuid4(), reason="Logout")


@pytest.mark.asyncio
async def test_revoke_by_token_family(request_context, refresh_token_provider: RefreshTokenProvider):
    now = datetime.datetime.now(datetime.timezone.utc)
    rt = refresh_token_provider._generate_token()
    rt_hash = refresh_token_provider._hash_token(rt)
    found = RefreshTokenData(
        user_id=uuid4(),
        device_id=uuid4(),
        family_id=uuid4(),
        token_hash=rt_hash,
        expires_at=now + datetime.timedelta(days=1),
        last_used_at=now,
    )
    # after hashing, provider looks up by token_hash, so mock return
    refresh_token_provider._session = SessionMock()
    refresh_token_provider._session.select(PortalRefreshToken).where(PortalRefreshToken.token_hash == found.token_hash).mock_fetchrow(return_value=found)
    # revoke family call
    refresh_token_provider._session.update(PortalRefreshToken).where(PortalRefreshToken.id == found.id).values(revoked_at=now, revoked_reason="Logout").mock()
    result = await refresh_token_provider.revoke_by_token(token=rt, revoke_family=True)
    assert result is True
