"""
Fixture for JWTProvider from Container.
"""
import pytest

from portal.container import Container
from portal.providers.jwt_provider import JWTProvider


@pytest.fixture
def jwt_provider(container: Container) -> JWTProvider:
    return container.jwt_provider()


