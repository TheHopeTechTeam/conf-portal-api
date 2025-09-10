"""
Model of the user table
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from portal.libs.consts.enums import Gender, ResourceType
from portal.libs.database.orm import ModelBase, Base
from .mixins import AuditMixin, DeletedMixin, RemarkMixin, DescriptionMixin, BaseMixin, SortableMixin


class PortalUser(ModelBase, RemarkMixin, DeletedMixin, AuditMixin):
    """Portal User Model"""
    phone_number = Column(
        sa.String(16),
        nullable=False,
        unique=True,
        comment="Phone number, unique identifier"
    )
    email = Column(sa.String(255), nullable=True, unique=True, comment="Email, unique identifier")
    password_hash = Column(sa.String(512), nullable=True, comment="Password hash")
    salt = Column(sa.String(128), nullable=True, comment="Salt for password hash")
    verified = Column(sa.Boolean, default=False, comment="Is verified")
    is_active = Column(sa.Boolean, default=True, index=True, comment="Is active")
    is_superuser = Column(sa.Boolean, default=False, comment="Is superuser")  # Top-level admin can access all resources in the admin panel
    is_admin = Column(sa.Boolean, default=False, comment="Is admin")  # Can access the admin panel
    password_changed_at = Column(sa.TIMESTAMP(timezone=True), comment="Password last changed time")
    password_expires_at = Column(sa.TIMESTAMP(timezone=True), comment="Password expiration time")
    last_login_at = Column(sa.TIMESTAMP(timezone=True), comment="Last login")

    # Relationships
    roles = relationship("PortalRole", secondary=lambda: PortalUserRole.__table__, back_populates="users", passive_deletes=True)


class PortalUserProfile(ModelBase, DeletedMixin, AuditMixin, DescriptionMixin):
    """Portal User Profile Model"""
    user_id = Column(
        UUID,
        sa.ForeignKey(PortalUser.id, ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="User ID",
        index=True
    )
    display_name = Column(sa.String(64), comment="Display name")
    gender = Column(sa.Integer, default=Gender.UNKNOWN.value, comment="Refer to Gender enum")
    is_ministry = Column(sa.Boolean, nullable=False, server_default=sa.text('false'), comment="Is ministry")


class PortalThirdPartyProvider(ModelBase, DeletedMixin, AuditMixin, RemarkMixin):
    """Portal Third Party Provider Model"""
    name = Column(sa.String(16), nullable=False, unique=True, comment="Provider name, Enum: Provider")


class PortalUserThirdPartyAuth(ModelBase, DeletedMixin, AuditMixin):
    """Portal User Third Party Auth Model"""
    __extra_table_args__ = (
        sa.UniqueConstraint("user_id", "provider_id", "provider_uid"),
    )
    user_id = Column(
        UUID,
        sa.ForeignKey(PortalUser.id, ondelete="CASCADE", name="fk_user_third_party_auth_user"),
        nullable=False,
        comment="User ID",
        index=True
    )
    provider_id = Column(
        UUID,
        sa.ForeignKey(PortalThirdPartyProvider.id, ondelete="CASCADE", name="fk_user_third_party_auth_provider"),
        nullable=False,
        comment="Provider ID",
        index=True
    )
    provider_uid = Column(sa.String(255), nullable=False, comment="Provider UID")
    access_token = Column(sa.String(255), comment="Access token")
    refresh_token = Column(sa.String(255), comment="Refresh token")
    token_expires_at = Column(sa.TIMESTAMP(timezone=True), comment="Token expiration time")
    additional_data = Column(JSONB, comment="Additional data")


class PortalRole(ModelBase, BaseMixin):
    """Portal Role Model for RBAC"""
    code = Column(sa.String(32), nullable=False, unique=True, comment="Role code")
    name = Column(sa.String(64), comment="Role name")
    is_active = Column(sa.Boolean, default=True, comment="Is role active")
    # Relationships
    users = relationship("PortalUser", secondary=lambda: PortalUserRole.__table__, back_populates="roles", passive_deletes=True)
    permissions = relationship("PortalPermission", secondary=lambda: PortalRolePermission.__table__, back_populates="roles", passive_deletes=True)


class PortalResource(ModelBase, BaseMixin, SortableMixin):
    """
    Portal Resource Model for RBAC
    Example:
        key: SYSTEM_USER, SYSTEM_ROLE, SYSTEM_PERMISSION
        code: system:user, system:role, system:permission
    """
    pid = Column(UUID, sa.ForeignKey("portal_resource.id", ondelete="CASCADE"), comment="Parent resource id")
    name = Column(sa.String(64), comment="Resource name")
    key = Column(sa.String(128), nullable=False, unique=True, comment="Resource key and front-end corresponding")
    code = Column(sa.String(32), nullable=False, unique=True, comment="Resource code (e.g., user, course, article)")
    icon = Column(sa.String(32), comment="Resource icon")
    path = Column(sa.String(256), comment="Resource path")
    type = Column(sa.Integer, default=ResourceType.GENERAL.value, nullable=False, comment="Resource type, Enum: ResourceType")
    is_visible = Column(sa.Boolean, nullable=False, server_default=sa.text("true"), comment="Is resource visible")
    children = relationship("PortalResource", passive_deletes=True)


class PortalVerb(ModelBase, BaseMixin):
    """Portal Verb Model for RBAC"""
    action = Column(sa.String(32), nullable=False, unique=True, comment="Verb action (e.g., create, read, update, delete)")
    display_name = Column(sa.String(64), comment="Display name")
    is_active = Column(sa.Boolean, default=True, comment="Is verb active")


class PortalPermission(ModelBase, BaseMixin):
    """Portal Permission Model for RBAC"""
    __extra_table_args__ = (
        sa.UniqueConstraint("resource_id", "verb_id"),
    )
    resource_id = Column(UUID, sa.ForeignKey(PortalResource.id, ondelete="CASCADE"), nullable=False, comment="Resource ID", index=True)
    verb_id = Column(UUID, sa.ForeignKey(PortalVerb.id, ondelete="CASCADE"), nullable=False, comment="Verb ID", index=True)
    code = Column(sa.String(128), nullable=False, unique=True, comment="Permission Code (e.g., user:read)")
    display_name = Column(sa.String(128), comment="Display name")
    is_active = Column(sa.Boolean, default=True, comment="Is permission active")

    # Relationships
    roles = relationship("PortalRole", secondary=lambda: PortalRolePermission.__table__, back_populates="permissions", passive_deletes=True)


class PortalUserRole(Base):
    """Association object for User-Role relationship"""
    user_id = Column(
        UUID,
        sa.ForeignKey(PortalUser.id, ondelete='CASCADE'),
        nullable=False,
        index=True,
        primary_key=True
    )
    role_id = Column(
        UUID,
        sa.ForeignKey(PortalRole.id, ondelete='CASCADE'),
        nullable=False,
        index=True,
        primary_key=True
    )


class PortalRolePermission(Base):
    """Association object for Role-Permission relationship"""
    __extra_table_args__ = (
        sa.UniqueConstraint('role_id', 'permission_id'),
    )
    role_id = Column(
        UUID,
        sa.ForeignKey(PortalRole.id, ondelete='CASCADE'),
        nullable=False,
        index=True,
        primary_key=True
    )
    permission_id = Column(
        UUID,
        sa.ForeignKey(PortalPermission.id, ondelete='CASCADE'),
        nullable=False,
        index=True,
        primary_key=True
    )
    expire_date = Column(sa.DateTime(timezone=True), index=True, comment='Expiration time, can be used for temporary authorization')
