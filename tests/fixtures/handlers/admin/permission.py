"""
Fixtures for admin permission handler tests.
"""
import pytest

from portal.container import Container
from portal.handlers import AdminPermissionHandler


@pytest.fixture
def admin_permission_handler(container: Container) -> AdminPermissionHandler:
    handler: AdminPermissionHandler = container.admin_permission_handler()
    return handler


