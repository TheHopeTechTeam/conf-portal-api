"""
Fixture for all providers.
"""
import pytest

from portal.container import Container
from portal.providers.jwt_provider import JWTProvider
from portal.providers.password_provider import PasswordProvider
from portal.providers.refresh_token_provider import RefreshTokenProvider
from portal.providers.thehope_ticket_provider import TheHopeTicketProvider
from portal.providers.token_blacklist_provider import TokenBlacklistProvider


@pytest.fixture
def jwt_provider(container: Container) -> JWTProvider:
    return container.jwt_provider()


@pytest.fixture
def password_provider(container: Container) -> PasswordProvider:
    return container.password_provider()


@pytest.fixture
def refresh_token_provider(container: Container) -> RefreshTokenProvider:
    return container.refresh_token_provider()


@pytest.fixture
def token_blacklist_provider(container: Container) -> TokenBlacklistProvider:
    return container.token_blacklist_provider()


@pytest.fixture
def thehope_ticket_provider(container: Container) -> TheHopeTicketProvider:
    return container.thehope_ticket_provider()
