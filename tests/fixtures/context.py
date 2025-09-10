"""
Shared request context fixtures for tests.
"""
from uuid import UUID

import pytest

from portal.libs.consts.enums import Gender
from portal.libs.contexts.request_context import RequestContext, set_request_context, reset_request_context
from portal.libs.contexts.user_context import UserContext, set_user_context, reset_user_context


@pytest.fixture(autouse=True)
def request_context():
    request_context = RequestContext(
        ip="127.0.0.1",
        client_ip="127.0.0.1",
        user_agent="pytest/ua"
    )
    token = set_request_context(request_context)
    try:
        yield request_context
    finally:
        reset_request_context(token)


@pytest.fixture
def user_context():
    user_context = UserContext(
        user_id=UUID("d5d4500e-e9ce-4774-abf1-9e1cb503f628"),
        phone_number="+14162345678",
        email="test_admin1@example.com",
        verified=True,
        is_active=True,
        is_superuser=True,
        is_admin=True,
        last_login_at=None,
        display_name="Test Admin 1",
        gender=Gender.UNKNOWN,
        is_ministry=False,
        token=None,
        token_payload=None,
        username=None
    )
    token = set_user_context(user_context)
    try:
        yield user_context
    finally:
        reset_user_context(token)
