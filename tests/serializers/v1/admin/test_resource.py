"""
Tests for resource serializers.
"""
import uuid

import pytest
from pydantic import ValidationError

from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.v1.admin.resource import (
    ResourceItem,
    ResourcePages,
    ResourceList,
    ResourceTreeItem,
    ResourceTree,
    ResourceCreate,
    ResourceUpdate,
    ResourceBulkDelete,
    ResourceChangeSequence,
)


def test_valid_resource_item():
    """Test creating a valid ResourceItem."""
    resource_id = uuid.uuid4()
    parent_id = uuid.uuid4()

    resource = ResourceItem(
        id=resource_id,
        pid=parent_id,
        name="使用者管理",
        key="user_management",
        code="USER_MGMT",
        icon="fas fa-users",
        path="/admin/users",
        description="管理系統使用者",
        remark="使用者 CRUD 操作",
        sequence=1.0
    )

    assert resource.id == resource_id
    assert resource.pid == parent_id
    assert resource.name == "使用者管理"
    assert resource.key == "user_management"
    assert resource.code == "USER_MGMT"
    assert resource.icon == "fas fa-users"
    assert resource.path == "/admin/users"
    assert resource.description == "管理系統使用者"
    assert resource.remark == "使用者 CRUD 操作"
    assert resource.sequence == 1.0


def test_resource_item_without_optional_fields():
    """Test creating ResourceItem without optional fields."""
    resource = ResourceItem(
        pid=None,
        name="系統管理",
        key="system_management",
        code="SYS_MGMT",
        sequence=1.0
    )

    assert resource.pid is None
    assert resource.icon is None
    assert resource.path is None
    assert resource.description is None
    assert resource.remark is None


def test_valid_resource_pages():
    """Test creating a valid ResourcePages."""
    resource1 = ResourceItem(
        pid=None,
        name="系統管理",
        key="system_management",
        code="SYS_MGMT",
        sequence=1.0
    )

    resource2 = ResourceItem(
        pid=uuid.uuid4(),
        name="使用者管理",
        key="user_management",
        code="USER_MGMT",
        sequence=2.0
    )

    pages = ResourcePages(
        page=1,
        page_size=10,
        total=25,
        items=[resource1, resource2]
    )

    assert pages.page == 1
    assert pages.page_size == 10
    assert pages.total == 25
    assert len(pages.items) == 2
    assert pages.items[0].name == "系統管理"
    assert pages.items[1].name == "使用者管理"


def test_valid_resource_list():
    """Test creating a valid ResourceList."""
    resource1 = ResourceItem(
        pid=None,
        name="會議管理",
        key="conference_management",
        code="CONF_MGMT",
        sequence=1.0
    )

    resource2 = ResourceItem(
        pid=uuid.uuid4(),
        name="會議列表",
        key="conference_list",
        code="CONF_LIST",
        sequence=2.0
    )

    resource_list = ResourceList(items=[resource1, resource2])

    assert len(resource_list.items) == 2
    assert resource_list.items[0].name == "會議管理"
    assert resource_list.items[1].name == "會議列表"


def test_valid_single_level_tree_item():
    """Test creating a valid single level ResourceTreeItem."""
    tree_item = ResourceTreeItem(
        pid=None,
        name="系統管理",
        key="system_management",
        code="SYS_MGMT",
        sequence=1.0,
        children=None
    )

    assert tree_item.name == "系統管理"
    assert tree_item.children is None


def test_valid_two_level_tree_item():
    """Test creating a valid two level ResourceTreeItem."""
    child_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="使用者管理",
        key="user_management",
        code="USER_MGMT",
        sequence=1.0,
        children=None
    )

    parent_item = ResourceTreeItem(
        pid=None,
        name="系統管理",
        key="system_management",
        code="SYS_MGMT",
        sequence=1.0,
        children=[child_item]
    )

    assert parent_item.name == "系統管理"
    assert len(parent_item.children) == 1
    assert parent_item.children[0].name == "使用者管理"


def test_valid_three_level_tree_item():
    """Test creating a valid three level ResourceTreeItem."""
    # 第三層
    level3_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="新增使用者",
        key="create_user",
        code="CREATE_USER",
        sequence=1.0,
        children=None
    )

    # 第二層
    level2_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="使用者管理",
        key="user_management",
        code="USER_MGMT",
        sequence=1.0,
        children=[level3_item]
    )

    # 第一層
    level1_item = ResourceTreeItem(
        pid=None,
        name="系統管理",
        key="system_management",
        code="SYS_MGMT",
        sequence=1.0,
        children=[level2_item]
    )

    assert level1_item.name == "系統管理"
    assert len(level1_item.children) == 1
    assert level1_item.children[0].name == "使用者管理"
    assert len(level1_item.children[0].children) == 1
    assert level1_item.children[0].children[0].name == "新增使用者"


def test_invalid_four_level_tree_item():
    """Test that four level tree item raises ValidationError."""
    # 第四層
    level4_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="子功能",
        key="sub_function",
        code="SUB_FUNC",
        sequence=1.0,
        children=None
    )

    # 第三層
    level3_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="新增使用者",
        key="create_user",
        code="CREATE_USER",
        sequence=1.0,
        children=[level4_item]  # 這裡會觸發驗證錯誤
    )

    # 第二層
    level2_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="使用者管理",
        key="user_management",
        code="USER_MGMT",
        sequence=1.0,
        children=[level3_item]
    )

    # 第一層 - 這裡會因為第四層的存在而失敗
    with pytest.raises(ValidationError) as exc_info:
        ResourceTreeItem(
            pid=None,
            name="系統管理",
            key="system_management",
            code="SYS_MGMT",
            sequence=1.0,
            children=[level2_item]
        )

    assert "樹狀結構超過三層限制" in str(exc_info.value)


def test_valid_empty_tree():
    """Test creating an empty ResourceTree."""
    tree = ResourceTree(items=[])
    assert tree.items == []


def test_valid_single_level_tree():
    """Test creating a valid single level ResourceTree."""
    root_item = ResourceTreeItem(
        pid=None,
        name="系統管理",
        key="system_management",
        code="SYS_MGMT",
        sequence=1.0,
        children=None
    )

    tree = ResourceTree(items=[root_item])
    assert tree.items[0].name == "系統管理"


def test_valid_three_level_tree():
    """Test creating a valid three level ResourceTree."""
    # 第三層
    level3_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="新增使用者",
        key="create_user",
        code="CREATE_USER",
        sequence=1.0,
        children=None
    )

    # 第二層
    level2_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="使用者管理",
        key="user_management",
        code="USER_MGMT",
        sequence=1.0,
        children=[level3_item]
    )

    # 第一層
    root_item = ResourceTreeItem(
        pid=None,
        name="系統管理",
        key="system_management",
        code="SYS_MGMT",
        sequence=1.0,
        children=[level2_item]
    )

    tree = ResourceTree(items=[root_item])
    assert tree.items[0].name == "系統管理"


def test_invalid_four_level_tree():
    """Test that four level tree raises ValidationError."""
    # 第四層
    level4_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="子功能",
        key="sub_function",
        code="SUB_FUNC",
        sequence=1.0,
        children=None
    )

    # 第三層
    level3_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="新增使用者",
        key="create_user",
        code="CREATE_USER",
        sequence=1.0,
        children=[level4_item]
    )

    # 第二層
    level2_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="使用者管理",
        key="user_management",
        code="USER_MGMT",
        sequence=1.0,
        children=[level3_item]
    )

    # 第一層 - 這裡會因為第四層的存在而失敗
    with pytest.raises(ValidationError) as exc_info:
        ResourceTreeItem(
            pid=None,
            name="系統管理",
            key="system_management",
            code="SYS_MGMT",
            sequence=1.0,
            children=[level2_item]
        )

    assert "樹狀結構超過三層限制" in str(exc_info.value)


def test_valid_resource_create():
    """Test creating a valid ResourceCreate."""
    resource = ResourceCreate(
        pid=uuid.uuid4(),
        name="角色管理",
        key="role_management",
        code="ROLE_MGMT",
        icon="fas fa-user-tag",
        path="/admin/roles",
        description="管理系統角色權限",
        remark="角色與權限設定"
    )

    assert resource.name == "角色管理"
    assert resource.key == "role_management"
    assert resource.code == "ROLE_MGMT"
    assert resource.icon == "fas fa-user-tag"
    assert resource.path == "/admin/roles"
    assert resource.description == "管理系統角色權限"
    assert resource.remark == "角色與權限設定"


def test_resource_create_without_optional_fields():
    """Test creating ResourceCreate without optional fields."""
    resource = ResourceCreate(
        name="系統管理",
        key="system_management",
        code="SYS_MGMT"
    )

    assert resource.pid is None
    assert resource.icon is None
    assert resource.path is None
    assert resource.description is None
    assert resource.remark is None


def test_valid_resource_update():
    """Test creating a valid ResourceUpdate."""
    resource = ResourceUpdate(
        pid=uuid.uuid4(),
        name="角色管理 (更新)",
        key="role_management",
        code="ROLE_MGMT",
        icon="fas fa-user-tag",
        path="/admin/roles",
        description="管理系統角色權限 (已更新)",
        remark="角色與權限設定 - 最新版本"
    )

    assert resource.name == "角色管理 (更新)"
    assert resource.description == "管理系統角色權限 (已更新)"
    assert resource.remark == "角色與權限設定 - 最新版本"


def test_valid_resource_bulk_delete():
    """Test creating a valid ResourceBulkDelete."""
    resource_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]

    bulk_delete = ResourceBulkDelete(ids=resource_ids)

    assert len(bulk_delete.ids) == 3
    assert all(isinstance(id_, uuid.UUID) for id_ in bulk_delete.ids)


def test_valid_resource_change_sequence():
    """Test creating a valid ResourceChangeSequence."""
    resource_id = uuid.uuid4()
    another_id = uuid.uuid4()

    change_sequence = ResourceChangeSequence(
        id=resource_id,
        sequence=2.0,
        another_id=another_id,
        another_sequence=1.0
    )

    assert change_sequence.id == resource_id
    assert change_sequence.sequence == 2.0
    assert change_sequence.another_id == another_id
    assert change_sequence.another_sequence == 1.0


def test_complex_three_level_tree():
    """Test a complex three level tree with multiple children at each level."""
    # 第三層 - 多個子項目
    level3_items = [
        ResourceTreeItem(
            pid=uuid.uuid4(),
            name="新增使用者",
            key="create_user",
            code="CREATE_USER",
            sequence=1.0,
            children=None
        ),
        ResourceTreeItem(
            pid=uuid.uuid4(),
            name="編輯使用者",
            key="edit_user",
            code="EDIT_USER",
            sequence=2.0,
            children=None
        ),
        ResourceTreeItem(
            pid=uuid.uuid4(),
            name="刪除使用者",
            key="delete_user",
            code="DELETE_USER",
            sequence=3.0,
            children=None
        )
    ]

    # 第二層 - 多個子項目
    level2_items = [
        ResourceTreeItem(
            pid=uuid.uuid4(),
            name="使用者管理",
            key="user_management",
            code="USER_MGMT",
            sequence=1.0,
            children=level3_items
        ),
        ResourceTreeItem(
            pid=uuid.uuid4(),
            name="角色管理",
            key="role_management",
            code="ROLE_MGMT",
            sequence=2.0,
            children=None
        )
    ]

    # 第一層
    root_item = ResourceTreeItem(
        pid=None,
        name="系統管理",
        key="system_management",
        code="SYS_MGMT",
        sequence=1.0,
        children=level2_items
    )

    tree = ResourceTree(items=[root_item])

    # 驗證結構
    assert tree.items[0].name == "系統管理"
    assert len(tree.items[0].children) == 2
    assert tree.items[0].children[0].name == "使用者管理"
    assert tree.items[0].children[1].name == "角色管理"
    assert len(tree.items[0].children[0].children) == 3
    assert tree.items[0].children[0].children[0].name == "新增使用者"
    assert tree.items[0].children[0].children[1].name == "編輯使用者"
    assert tree.items[0].children[0].children[2].name == "刪除使用者"
    assert tree.items[0].children[1].children is None


def test_tree_with_mixed_depths():
    """Test tree where some branches have different depths."""
    # 第三層
    level3_item = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="新增使用者",
        key="create_user",
        code="CREATE_USER",
        sequence=1.0,
        children=None
    )

    # 第二層 - 一個有子項目，一個沒有
    level2_with_children = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="使用者管理",
        key="user_management",
        code="USER_MGMT",
        sequence=1.0,
        children=[level3_item]
    )

    level2_without_children = ResourceTreeItem(
        pid=uuid.uuid4(),
        name="角色管理",
        key="role_management",
        code="ROLE_MGMT",
        sequence=2.0,
        children=None
    )

    # 第一層
    root_item = ResourceTreeItem(
        pid=None,
        name="系統管理",
        key="system_management",
        code="SYS_MGMT",
        sequence=1.0,
        children=[level2_with_children, level2_without_children]
    )

    tree = ResourceTree(items=[root_item])

    # 驗證結構
    assert len(tree.items[0].children) == 2
    assert tree.items[0].children[0].children is not None
    assert tree.items[0].children[1].children is None
    assert len(tree.items[0].children[0].children) == 1


def test_resource_delete_without_reason():
    """Test creating DeleteBaseModel without reason."""
    with pytest.raises(ValueError) as exc_info:
        DeleteBaseModel(permanent=False)
    assert "Reason is required for non-permanent delete" in str(exc_info.value)


def test_resource_delete_with_reason():
    """Test creating DeleteBaseModel with reason."""
    model = DeleteBaseModel(permanent=False, reason="test reason")
    assert model.permanent is False
    assert model.reason == "test reason"


def test_resource_delete_permanent():
    """Test creating DeleteBaseModel with permanent True."""
    model = DeleteBaseModel(permanent=True)
    assert model.permanent is True
    assert model.reason is None
