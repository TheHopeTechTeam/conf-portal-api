"""
Fixtures for RefreshTokenProvider using Container with SessionMock override.
"""
import pytest

from portal.container import Container
from portal.providers.refresh_token_provider import RefreshTokenProvider


@pytest.fixture
def refresh_token_provider(container: Container) -> RefreshTokenProvider:
    return container.refresh_token_provider()


