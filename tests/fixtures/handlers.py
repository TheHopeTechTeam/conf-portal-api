"""
Fixtures for all handlers.
"""
import pytest

from portal.container import Container
from portal.handlers import (
    AdminAuthHandler,
    AdminPermissionHandler,
    AdminResourceHandler,
    AdminRoleHandler,
    AdminUserHandler
)


@pytest.fixture
def admin_auth_handler(user_context, container: Container) -> AdminAuthHandler:
    return container.admin_auth_handler()


@pytest.fixture
def admin_permission_handler(user_context, container: Container) -> AdminPermissionHandler:
    return container.admin_permission_handler()


@pytest.fixture
def admin_resource_handler(user_context, container: Container) -> AdminResourceHandler:
    return container.admin_resource_handler()


@pytest.fixture
def admin_role_handler(user_context, container: Container) -> AdminRoleHandler:
    return container.admin_role_handler()


@pytest.fixture
def admin_user_handler(user_context, container: Container) -> AdminUserHandler:
    return container.admin_user_handler()
