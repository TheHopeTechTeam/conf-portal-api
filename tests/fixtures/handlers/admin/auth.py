"""
Fixtures for account handler tests.
"""
import pytest

from portal.container import Container
from portal.handlers import AdminAuthHandler


@pytest.fixture
def admin_auth_handler(container: Container) -> AdminAuthHandler:
    """Get the admin auth handler."""
    return container.admin_auth_handler()
