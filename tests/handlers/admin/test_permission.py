"""
Test admin permission handler
"""
from unittest.mock import AsyncMock
from uuid import uuid4, UUID

import pytest

from portal.libs.consts.cache_keys import create_permission_key
from portal.models import PortalPermission, PortalVerb, PortalResource, PortalRole, PortalUser
from portal.schemas.permission import PermissionBase
from portal.schemas.user import SUserSensitive


@pytest.mark.asyncio
async def test_init_user_permissions_cache_regular_admin(
    admin_permission_handler,
    mocker
):
    user = SUserSensitive(
        id=UUID("385dfc73-1379-43b1-988f-603a791ec236"),
        phone_number="+886912345678",
        email="test@example.com",
        password_hash="hashed_password",
        salt=None,
        verified=True,
        is_active=True,
        is_superuser=False,
        is_admin=True,
        password_changed_at=None,
        password_expires_at=None,
        last_login_at=None
    )
    await admin_permission_handler.init_user_permissions_cache(user, 3600)
    assert True


@pytest.mark.asyncio
async def test_init_user_permissions_cache_superuser(
    admin_permission_handler,
    mocker
):
    user = SUserSensitive(
        id=uuid4(),
        phone_number="+886912345678",
        email="test@example.com",
        password_hash="hashed_password",
        salt=None,
        verified=True,
        is_active=True,
        is_superuser=True,
        is_admin=True,
        password_changed_at=None,
        password_expires_at=None,
        last_login_at=None
    )

    mocked_permissions = [
        {"code": "resource.manage", "action": "manage", "resource_code": "resource"},
    ]

    from portal.libs.database.session_mock import SessionMock
    admin_permission_handler._session = SessionMock()
    admin_permission_handler._session.select(
        PortalPermission.code,
        PortalVerb.action,
        PortalResource.code.label("resource_code"),
    ).outerjoin(PortalResource, PortalPermission.resource_id == PortalResource.id) \
        .outerjoin(PortalVerb, PortalPermission.verb_id == PortalVerb.id) \
        .where(PortalPermission.is_active == True) \
        .mock_fetch([PermissionBase(**p) for p in mocked_permissions])

    key = create_permission_key(str(user.id))
    admin_permission_handler._redis.hset = AsyncMock()

    await admin_permission_handler.init_user_permissions_cache(user, 100)

    assert admin_permission_handler._redis.hset.await_count == len(mocked_permissions)
    for p in mocked_permissions:
        admin_permission_handler._redis.hset.assert_any_await(key, p["code"], PermissionBase(**p).model_dump_json())


@pytest.mark.asyncio
async def test_init_user_permissions_cache_no_permissions(
    admin_permission_handler,
    mocker
):
    user = SUserSensitive(
        id=uuid4(),
        phone_number="+886912345678",
        email="test@example.com",
        password_hash="hashed_password",
        salt=None,
        verified=True,
        is_active=True,
        is_superuser=False,
        is_admin=True,
        password_changed_at=None,
        password_expires_at=None,
        last_login_at=None
    )

    from portal.libs.database.session_mock import SessionMock
    admin_permission_handler._session = SessionMock()
    admin_permission_handler._session.select(
        PortalPermission.code,
        PortalVerb.action,
        PortalResource.code.label("resource_code"),
    ).outerjoin(PortalResource, PortalPermission.resource_id == PortalResource.id) \
        .outerjoin(PortalVerb, PortalPermission.verb_id == PortalVerb.id) \
        .join(PortalPermission.roles) \
        .join(PortalRole.users) \
        .where(PortalUser.id == user.id) \
        .where(PortalRole.is_active.is_(True)) \
        .where(PortalPermission.is_active == True) \
        .where(PortalResource.is_visible == True) \
        .where(PortalVerb.is_active == True) \
        .where(PortalPermission.is_active == True) \
        .where(PortalUser.is_active == True) \
        .where(PortalUser.is_deleted == False) \
        .mock_fetch([])

    admin_permission_handler._redis.hset = AsyncMock()
    admin_permission_handler._redis.expire = AsyncMock()

    await admin_permission_handler.init_user_permissions_cache(user, 100)

    admin_permission_handler._redis.hset.assert_not_called()
    admin_permission_handler._redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_clear_user_permissions_cache(
    admin_permission_handler,
    mocker
):
    user_id = uuid4()
    key = create_permission_key(str(user_id))
    admin_permission_handler._redis.delete = AsyncMock()
    await admin_permission_handler.clear_user_permissions_cache(user_id)
    admin_permission_handler._redis.delete.assert_awaited_once_with(key)


@pytest.mark.asyncio
async def test_get_permission_by_id(
    admin_permission_handler,
):
    """

    :param admin_permission_handler:
    :return:
    """
    permission_id = UUID("b30d72f6-0425-44a8-9f25-2839b0684c92")
    permission = await admin_permission_handler.get_permission_by_id(permission_id)
    assert permission.id == permission_id
