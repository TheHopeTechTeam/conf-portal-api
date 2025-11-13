"""
Tests for JWTProvider.
"""
from datetime import timedelta
from uuid import uuid4

import pytest

from portal.config import settings
from portal.libs.consts.enums import AccessTokenAudType
from portal.providers.jwt_provider import JWTProvider
from portal.container import Container


def _make_admin_access_token(jwt_provider: JWTProvider):
    user_id = uuid4()
    family_id = uuid4()
    return jwt_provider.create_access_token(
        user_id=user_id,
        email="admin@example.com",
        display_name="Admin",
        family_id=family_id,
        roles=["admin"],
        permissions=[
            "system:user:create",
            "system:user:edit",
            "system:user:delete",
            "system:user:view",
        ],
        aud_type=AccessTokenAudType.ADMIN
    )


def test_create_and_verify_admin_access_token(jwt_provider: JWTProvider):
    token = _make_admin_access_token(jwt_provider)
    payload = jwt_provider.verify_token(token)
    assert payload is not None
    assert payload.get("sub").endswith("admin_access")
    assert jwt_provider.is_admin_token(token) is True


def test_is_token_expired_with_past_expiration(jwt_provider: JWTProvider):
    token = jwt_provider.create_access_token(
        user_id=uuid4(),
        email="a@b.com",
        display_name="A",
        family_id=uuid4(),
        expires_delta=timedelta(seconds=-1),  # already expired
        aud_type=AccessTokenAudType.ADMIN
    )
    assert jwt_provider.is_token_expired(token) is True


@pytest.mark.asyncio
async def test_verify_token_with_blacklist(jwt_provider: JWTProvider, container: Container):
    token = _make_admin_access_token(jwt_provider)
    # blacklist token for 60s
    expires = jwt_provider.get_token_expiration(token)
    assert expires is not None
    await container.token_blacklist_provider().add_to_blacklist(token, expires)

    payload = await jwt_provider.verify_token_with_blacklist(token)
    assert payload is None


