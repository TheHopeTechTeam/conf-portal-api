"""
Fixture for TokenBlacklistProvider from Container using real Redis connection.
"""
import pytest

from portal.container import Container
from portal.providers.token_blacklist_provider import TokenBlacklistProvider


@pytest.fixture
def token_blacklist_provider(container: Container) -> TokenBlacklistProvider:
    return container.token_blacklist_provider()


