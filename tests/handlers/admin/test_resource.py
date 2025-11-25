"""
Test admin resource handler
"""
import uuid
import sqlalchemy as sa

import pytest
from pytest_mock import MockerFixture

from portal.handlers import AdminResourceHandler
from portal.libs.consts.enums import ResourceType
from portal.libs.contexts.user_context import UserContext
from portal.libs.database.session_mock import SessionMock
from portal.models import PortalPermission, PortalResource, PortalRole, PortalRolePermission, PortalUser
from portal.serializers.v1.admin.resource import AdminResourceItem, AdminResourceTreeItem


@pytest.mark.asyncio
async def test_get_user_permission_menus(admin_resource_handler: AdminResourceHandler):
    """
    Superuser should return menus via get_resource_menus().
    """
    # Arrange: stub DB calls to return empty list
    admin_resource_handler._session = SessionMock()
    admin_resource_handler._session.select(
        PortalResource.id,
        PortalResource.pid,
        PortalResource.name,
        PortalResource.key,
        PortalResource.code,
        PortalResource.icon,
        PortalResource.path,
        PortalResource.type,
        PortalResource.sequence
    ).where(PortalResource.is_deleted == False).order_by(PortalResource.sequence).mock_fetch([])

    # Act
    result = await admin_resource_handler.get_user_permission_menus()

    # Assert
    assert isinstance(result, list)
    assert result == []


@pytest.mark.asyncio
async def test_get_admin_resource_tree(admin_resource_handler: AdminResourceHandler, mocker: MockerFixture):
    """
    Superuser should get a tree built from get_resource_menus().
    """
    # Arrange
    rid_root = uuid.uuid4()
    rid_child = uuid.uuid4()
    resources = [
        AdminResourceItem(
            id=rid_root,
            pid=None,
            name="Root",
            key="root",
            code="root",
            type=ResourceType.GENERAL,
            sequence=1.0,
        ),
        AdminResourceItem(
            id=rid_child,
            pid=rid_root,
            name="Child",
            key="child",
            code="child",
            type=ResourceType.GENERAL,
            sequence=1.0,
        ),
    ]
    mocker.patch.object(admin_resource_handler, "get_resource_menus", return_value=resources)

    # Act
    tree = await admin_resource_handler.get_admin_resource_tree()

    # Assert
    assert tree.items and len(tree.items) == 1
    assert tree.items[0].name == "Root"
    assert tree.items[0].children and tree.items[0].children[0].name == "Child"


def test_build_tree_hierarchy_and_sorting():
    """
    build_tree should nest by pid and sort by (sequence, name).
    """
    rid_root = uuid.uuid4()
    rid_c1 = uuid.uuid4()
    rid_c2 = uuid.uuid4()
    rid_c2a = uuid.uuid4()

    items: list[AdminResourceItem] = [
        AdminResourceItem(
            id=rid_root,
            pid=None,
            name="Root",
            key="root",
            code="root",
            type=ResourceType.GENERAL,
            sequence=1.0,
        ),
        AdminResourceItem(
            id=rid_c2,
            pid=rid_root,
            name="Zeta",  # same sequence as c1 but name sorts after Alpha
            key="zeta",
            code="zeta",
            type=ResourceType.GENERAL,
            sequence=2.0,
        ),
        AdminResourceItem(
            id=rid_c1,
            pid=rid_root,
            name="Alpha",
            key="alpha",
            code="alpha",
            type=ResourceType.GENERAL,
            sequence=2.0,
        ),
        AdminResourceItem(
            id=rid_c2a,
            pid=rid_c2,
            name="Sub",
            key="sub",
            code="sub",
            type=ResourceType.GENERAL,
            sequence=1.5,
        ),
    ]

    roots = AdminResourceHandler.build_tree(items)

    assert len(roots) == 1
    assert roots[0].id == rid_root
    assert roots[0].children is not None
    # children sorted by (sequence, name): Alpha then Zeta
    assert [c.name for c in roots[0].children] == ["Alpha", "Zeta"]
    # nested child under Zeta
    zeta = [c for c in roots[0].children if c.id == rid_c2][0]
    assert zeta.children and zeta.children[0].id == rid_c2a


@pytest.mark.asyncio
async def test_get_admin_resource_tree_unauthorized(admin_resource_handler: AdminResourceHandler):
    """
    Non-admin and non-superuser should be unauthorized.
    """
    # Replace handler context directly to avoid container wiring
    admin_resource_handler._user_ctx = UserContext(
        user_id=uuid.uuid4(),
        is_admin=False,
        is_superuser=False,
        is_active=True,
        verified=True,
    )

    with pytest.raises(Exception):
        # exact exception class is UnauthorizedException, avoid direct import coupling
        await admin_resource_handler.get_admin_resource_tree()


@pytest.mark.asyncio
async def test_get_resource_menus_query(admin_resource_handler: AdminResourceHandler):
    """
    get_resource_menus should fetch visible resources and map to ResourceItem.
    """
    # Arrange
    admin_resource_handler._session = SessionMock()
    rid = uuid.uuid4()
    mocked = [
        AdminResourceItem(
            id=rid,
            pid=None,
            name="Root",
            key="root",
            code="root",
            type=ResourceType.GENERAL,
            sequence=1.0,
        )
    ]

    admin_resource_handler._session.select(
        PortalResource.id,
        PortalResource.pid,
        PortalResource.name,
        PortalResource.key,
        PortalResource.code,
        PortalResource.icon,
        PortalResource.path,
        PortalResource.type,
        PortalResource.sequence
    ).where(PortalResource.is_deleted == False).order_by(PortalResource.sequence).mock_fetch(mocked)

    # Act
    result = await admin_resource_handler.get_resource_menus()

    # Assert
    assert result == mocked


@pytest.mark.asyncio
async def test_get_resource_by_user_id_query(admin_resource_handler: AdminResourceHandler):
    """
    get_resource_by_user_id should join through roles/permissions and return mapped items.
    """
    # Arrange
    admin_resource_handler._session = SessionMock()
    uid = uuid.uuid4()
    rid = uuid.uuid4()
    mocked = [
        AdminResourceItem(
            id=rid,
            pid=None,
            name="Root",
            key="root",
            code="root",
            type=ResourceType.GENERAL,
            sequence=1.0,
        )
    ]

    admin_resource_handler._session.select(
        PortalResource.id,
        PortalResource.pid,
        PortalResource.name,
        PortalResource.key,
        PortalResource.code,
        PortalResource.icon,
        PortalResource.path,
        PortalResource.sequence
    ).select_from(PortalUser).join(PortalUser.roles).outerjoin(
        PortalRolePermission, PortalRolePermission.role_id == PortalRole.id
    ).outerjoin(
        PortalPermission, PortalPermission.id == PortalRolePermission.permission_id
    ).outerjoin(
        PortalResource, PortalPermission.resource_id == PortalResource.id
    ).where(
        PortalUser.id == uid
    ).where(
        PortalResource.is_deleted == False
    ).where(
        PortalResource.is_visible == True
    ).where(
        PortalPermission.is_active == True
    ).where(
        PortalPermission.is_deleted == False
    ).where(
        PortalRole.is_active == True
    ).where(
        PortalRole.is_deleted == False
    ).where(
        sa.or_(
            PortalRolePermission.expire_date.is_(None),
            PortalRolePermission.expire_date > sa.func.now(),
        )
    ).order_by(
        PortalResource.sequence
    ).mock_fetch(mocked)

    # Act
    result = await admin_resource_handler.get_resource_by_user_id(uid)

    # Assert
    assert result == mocked


@pytest.mark.asyncio
async def test_get_user_permission_menus_admin_non_superuser(admin_resource_handler: AdminResourceHandler, mocker: MockerFixture):
    """
    Admin but not superuser should fetch by user_id.
    """
    # Set context to admin only
    admin_resource_handler._user_ctx.is_superuser = False
    admin_resource_handler._user_ctx.is_admin = True

    mocked = [
        AdminResourceItem(
            id=uuid.uuid4(),
            pid=None,
            name="Root",
            key="root",
            code="root",
            type=ResourceType.GENERAL,
            sequence=1.0,
        )
    ]
    spy = mocker.patch.object(admin_resource_handler, "get_resource_by_user_id", return_value=mocked)

    result = await admin_resource_handler.get_user_permission_menus()

    spy.assert_called_once_with(user_id=admin_resource_handler._user_ctx.user_id)
    assert result == mocked
