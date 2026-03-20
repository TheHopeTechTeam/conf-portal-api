"""
Test send sign-in link event handler.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from portal.handlers.events.send_sign_in_link import SendSignInLinkEventHandler
from portal.libs.events.types import SendSignInLinkEvent


class _SelectQuery:
    def where(self, *args, **kwargs):
        return self

    async def fetchval(self):
        return self._value

    def __init__(self, value):
        self._value = value


@pytest.mark.asyncio
async def test_handle_use_display_name_when_ticket_updates_profile():
    user_id = uuid.uuid4()
    session = MagicMock()
    session.select.return_value = _SelectQuery("Ticket User")

    user_handler = MagicMock()
    user_handler.ensure_portal_user_and_profile_by_email = AsyncMock(return_value=user_id)

    ticket_handler = MagicMock()
    ticket_handler.sync_user_ticket = AsyncMock()

    firebase_provider = MagicMock()
    firebase_provider.generate_sign_in_with_email_link.return_value = "https://firebase.link/auth"

    login_verification_email_provider = MagicMock()
    login_verification_email_provider.send_login_verification_email = AsyncMock()

    handler = SendSignInLinkEventHandler(
        session=session,
        user_handler=user_handler,
        ticket_handler=ticket_handler,
        firebase_provider=firebase_provider,
        login_verification_email_provider=login_verification_email_provider,
    )

    event = SendSignInLinkEvent(email="member@example.com")
    await handler.handle(event=event)

    login_verification_email_provider.send_login_verification_email.assert_awaited_once()
    called_kwargs = login_verification_email_provider.send_login_verification_email.await_args.kwargs
    assert called_kwargs["member_name"] == "Ticket User"
    assert called_kwargs["to_email"] == "member@example.com"


@pytest.mark.asyncio
async def test_handle_fallback_member_name_to_email_when_display_name_missing():
    user_id = uuid.uuid4()
    session = MagicMock()
    session.select.return_value = _SelectQuery(None)

    user_handler = MagicMock()
    user_handler.ensure_portal_user_and_profile_by_email = AsyncMock(return_value=user_id)

    ticket_handler = MagicMock()
    ticket_handler.sync_user_ticket = AsyncMock()

    firebase_provider = MagicMock()
    firebase_provider.generate_sign_in_with_email_link.return_value = "https://firebase.link/auth"

    login_verification_email_provider = MagicMock()
    login_verification_email_provider.send_login_verification_email = AsyncMock()

    handler = SendSignInLinkEventHandler(
        session=session,
        user_handler=user_handler,
        ticket_handler=ticket_handler,
        firebase_provider=firebase_provider,
        login_verification_email_provider=login_verification_email_provider,
    )

    event = SendSignInLinkEvent(email="fallback@example.com")
    await handler.handle(event=event)

    login_verification_email_provider.send_login_verification_email.assert_awaited_once()
    called_kwargs = login_verification_email_provider.send_login_verification_email.await_args.kwargs
    assert called_kwargs["member_name"] == "fallback@example.com"
