"""
Tests for user auth handler.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from portal.exceptions.responses import ApiBaseException
from portal.handlers.user_auth import UserAuthHandler
from portal.libs.consts.enums import AuthProvider, Gender
from portal.schemas.auth import FirebaseObject, FirebaseTokenPayload
from portal.schemas.user import SAuthProvider, SUserThirdParty
from portal.serializers.mixins import TokenResponse
from portal.serializers.v1.user import UserLogin


class _InsertChain:
    def values(self, *args, **kwargs):
        return self

    def on_conflict_do_update(self, *args, **kwargs):
        return self

    async def execute(self):
        return None


def _make_token_payload(email: str = "member@example.com") -> FirebaseTokenPayload:
    return FirebaseTokenPayload(
        name="Member",
        aud="aud",
        auth_time=1,
        email_verified=True,
        email=email,
        exp=2,
        firebase=FirebaseObject(identities={}, sign_in_provider="password"),
        iat=1,
        iss="iss",
        phone_number=None,
        picture=None,
        sub="sub",
        user_id="firebase_uid_1",
    )


def _make_user(email: str, verified: bool) -> SUserThirdParty:
    return SUserThirdParty(
        id=uuid.uuid4(),
        phone_number=None,
        email=email,
        verified=verified,
        is_active=True,
        is_superuser=False,
        is_admin=False,
        last_login_at=None,
        display_name=None,
        gender=Gender.UNKNOWN,
        is_ministry=False,
        provider_id=uuid.uuid4(),
        provider=AuthProvider.FIREBASE.value,
        provider_uid="firebase_uid_1",
        additional_data={},
    )


def _make_handler() -> UserAuthHandler:
    session = MagicMock()
    session.insert.return_value = _InsertChain()
    redis_client = MagicMock()
    redis_client.create.return_value = MagicMock()
    handler = UserAuthHandler(
        session=session,
        redis_client=redis_client,
        jwt_provider=MagicMock(),
        token_blacklist_provider=MagicMock(),
        refresh_token_provider=MagicMock(),
        user_handler=MagicMock(),
        fcm_device_handler=MagicMock(),
        firebase_provider=MagicMock(),
        login_verification_email_provider=MagicMock(),
    )
    return handler


@pytest.mark.asyncio
async def test_firebase_login_should_link_precreated_user_and_mark_verified():
    handler = _make_handler()
    token_payload = _make_token_payload()
    precreated_user = _make_user(email=token_payload.email, verified=False)
    refreshed_user = precreated_user.model_copy(update={"verified": True, "display_name": "Member"})
    provider = SAuthProvider(id=uuid.uuid4(), name=AuthProvider.FIREBASE.value)

    handler._third_party_provider = MagicMock()
    handler._third_party_provider.verify_firebase_token.return_value = token_payload
    handler.get_provider_by_name = AsyncMock(return_value=provider)
    handler._user_handler.get_user_detail_by_provider_info = AsyncMock(return_value=None)
    handler._user_handler.get_user_tp_detail_by_email = AsyncMock(side_effect=[precreated_user, refreshed_user])
    handler._user_handler.mark_user_verified = AsyncMock()
    handler._user_handler.update_last_login_at = AsyncMock()
    handler._user_handler.create_user = AsyncMock()
    handler.fcm_device_handler.bind_user_device = AsyncMock(return_value=uuid.uuid4())
    handler.get_token_info = AsyncMock(
        return_value=TokenResponse(
            access_token="access",
            refresh_token="refresh",
            token_type="bearer",
            expires_in=3600,
        )
    )

    model = UserLogin(
        login_method=AuthProvider.FIREBASE,
        firebase_token="token",
        device_id="device-key",
    )
    with patch("portal.handlers.user_auth.publish_event_in_background"):
        response = await handler.firebase_login(model=model)

    handler._user_handler.create_user.assert_not_called()
    handler._user_handler.mark_user_verified.assert_awaited_once_with(user_id=precreated_user.id)
    assert response.user.verified is True
    assert response.user.first_login is True


@pytest.mark.asyncio
async def test_firebase_login_should_create_user_when_not_found():
    handler = _make_handler()
    token_payload = _make_token_payload()
    created_user = _make_user(email=token_payload.email, verified=True)
    provider = SAuthProvider(id=uuid.uuid4(), name=AuthProvider.FIREBASE.value)

    handler._third_party_provider = MagicMock()
    handler._third_party_provider.verify_firebase_token.return_value = token_payload
    handler.get_provider_by_name = AsyncMock(return_value=provider)
    handler._user_handler.get_user_detail_by_provider_info = AsyncMock(return_value=None)
    handler._user_handler.get_user_tp_detail_by_email = AsyncMock(return_value=None)
    handler._user_handler.create_user = AsyncMock(return_value=created_user)
    handler.fcm_device_handler.bind_user_device = AsyncMock(return_value=uuid.uuid4())
    handler.get_token_info = AsyncMock(
        return_value=TokenResponse(
            access_token="access",
            refresh_token="refresh",
            token_type="bearer",
            expires_in=3600,
        )
    )

    model = UserLogin(
        login_method=AuthProvider.FIREBASE,
        firebase_token="token",
        device_id="device-key",
    )
    with patch("portal.handlers.user_auth.publish_event_in_background"):
        response = await handler.firebase_login(model=model)

    handler._user_handler.create_user.assert_awaited_once()
    assert response.user.first_login is True


@pytest.mark.asyncio
async def test_firebase_login_should_reject_when_email_missing():
    handler = _make_handler()
    token_payload = _make_token_payload(email=None)
    handler._third_party_provider = MagicMock()
    handler._third_party_provider.verify_firebase_token.return_value = token_payload

    model = UserLogin(
        login_method=AuthProvider.FIREBASE,
        firebase_token="token",
        device_id="device-key",
    )
    with pytest.raises(ApiBaseException):
        await handler.firebase_login(model=model)
