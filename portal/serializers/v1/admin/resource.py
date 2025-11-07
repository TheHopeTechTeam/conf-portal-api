"""
Resource serializers
"""
from typing import Optional
from uuid import UUID

from pydantic import Field, BaseModel, field_validator

from portal.libs.consts.enums import ResourceType
from portal.schemas.mixins import UUIDBaseModel, JSONStringMixinModel
from portal.serializers.mixins import PaginationBaseResponseModel


class ResourceBase(UUIDBaseModel):
    """ResourceBase"""
    name: str = Field(..., description="Name")
    key: str = Field(..., description="Key")
    code: str = Field(..., description="Code")
    icon: Optional[str] = Field(None, description="Icon")


class ResourceItem(ResourceBase):
    """ResourceItem"""
    pid: Optional[UUID] = Field(None, description="Parent resource id")
    path: Optional[str] = Field(None, description="Path")
    type: ResourceType = Field(..., description="Resource type")
    description: Optional[str] = Field(None, description="Description")
    remark: Optional[str] = Field(None, description="Remark")
    sequence: float = Field(..., description="Sequence")
    is_deleted: bool = Field(False, description="Is deleted")


class ResourceParent(ResourceBase, JSONStringMixinModel):
    """ResourceParent"""
    id: Optional[UUID] = Field(None, description="Resource id")
    name: Optional[str] = Field(None, description="Name")
    key: Optional[str] = Field(None, description="Key")
    code: Optional[str] = Field(None, description="Code")
    icon: Optional[str] = Field(None, description="Icon")


class ResourceDetail(ResourceItem):
    """ResourceDetail"""
    pid: Optional[UUID] = Field(None, description="Parent resource id", exclude=True)
    parent: Optional[ResourceParent] = Field(None, description="Parent resource")


class ResourcePages(PaginationBaseResponseModel):
    """ResourcePages"""
    items: Optional[list[ResourceItem]] = Field(..., description="Resource Items")


class ResourceList(BaseModel):
    """ResourceList"""
    items: Optional[list[ResourceItem]] = Field(..., description="Resource Items")


class ResourceTreeItem(ResourceItem):
    """Resource Tree Item"""
    children: Optional[list["ResourceTreeItem"]] = Field(None, description="Resource children")

    @field_validator('children')
    def validate_children_depth(cls, v):
        """validate children depth not exceed limit"""
        if v is not None:
            for child in v:
                cls.validate_node_depth(child, 1)  # start from second level
        return v

    @classmethod
    def validate_node_depth(cls, node: "ResourceTreeItem", current_depth: int):
        """validate node depth"""
        if current_depth > 2:
            raise ValueError("Tree structure exceeds three levels limit")

        if node.children:
            for child in node.children:
                cls.validate_node_depth(child, current_depth + 1)


class ResourceTree(BaseModel):
    """Resource Tree - Max 2 levels"""
    items: Optional[list[ResourceTreeItem]] = Field(None, description="Root resource items")

    @field_validator('items')
    def validate_tree_depth(cls, v):
        """validate tree depth not exceed limit"""
        if v:
            for root in v:
                ResourceTreeItem.validate_node_depth(root, 1)  # start from first level
        return v


class ResourceCreate(BaseModel):
    """ResourceCreate"""
    pid: Optional[UUID] = Field(None, description="Parent resource id")
    name: str = Field(..., description="Name")
    key: str = Field(..., description="Key")
    code: str = Field(..., description="Code")
    icon: str = Field(..., description="Icon")
    path: str = Field(..., description="Path")
    type: ResourceType = Field(..., description="Resource type")
    is_visible: bool = Field(True, description="Is visible")
    description: Optional[str] = Field(None, description="Description")
    remark: Optional[str] = Field(None, description="Remark")


class ResourceUpdate(ResourceCreate):
    """ResourceUpdate"""


class ResourceChangeParent(BaseModel):
    """ResourceChangeParent"""
    pid: UUID = Field(..., description="New parent resource ID")


class ResourceBulkDelete(BaseModel):
    """ResourceBulkDelete"""
    ids: list[UUID] = Field(..., description="Resource IDs to delete")


class ResourceChangeSequence(BaseModel):
    """ResourceChangeSequence"""
    id: UUID = Field(..., description="Resource ID")
    sequence: float = Field(..., description="New sequence")
    another_id: UUID = Field(..., description="Another resource ID to swap sequence with")
    another_sequence: float = Field(..., description="Another resource's current sequence")
