"""
Fixture for PasswordProvider.
"""
import pytest

from portal.container import Container
from portal.providers.password_provider import PasswordProvider


@pytest.fixture
def password_provider(container: Container) -> PasswordProvider:
    """
    Fixture for PasswordProvider
    :param container:
    :return:
    """
    return container.password_provider()


